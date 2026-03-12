"""
Nexus AI — Excel Service
Генерация .xlsx файлов с данными о мероприятии
"""
import os
import logging
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

import re
logger = logging.getLogger(__name__)

def sanitize_for_excel(value):
    """Удаляет управляющие символы, которые ломают openpyxl."""
    if not isinstance(value, str):
        return value
    return re.sub(r'[\000-\010\013\014\016-\037]', '', value)

def generate_event_xlsx(event_title: str, event_date: str, event_location: str, candidates: list) -> str:
    """
    Генерирует Excel файл и возвращает путь к нему.
    Путь: /tmp/event_<id>_<timestamp>.xlsx
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Кандидаты"

    # Заголовок мероприятия (теперь на 9 колонок)
    ws.merge_cells("A1:I1")
    ws["A1"] = f"Мероприятие: {event_title} ({event_date}) — {event_location}"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A1"].alignment = Alignment(horizontal="center")

    # Шапка таблицы
    headers = ["ФИО", "Пол", "Телефон", "TG Username", "Приход", "Уход", "Отработано (ч)", "Ставка/час", "К оплате"]
    ws.append(headers)
    
    # Стили для шапки
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
    
    for cell in ws[2]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # Переменная для ставки (по умолчанию, можно будет потом добавить)
    default_rate = 100000

    # Данные
    row_idx = 3
    for c in candidates:
        profile = c.get("candidates", {}) or {}
        # Используем сохраненное полное имя, если оно есть
        db_full_name = profile.get("full_name")
        if db_full_name:
            full_name = sanitize_for_excel(db_full_name)
        else:
            first_name = profile.get("first_name", "")
            last_name = profile.get("last_name", "")
            full_name = sanitize_for_excel(f"{first_name} {last_name}".strip())
            
        gender_raw = profile.get("gender", "—")
        gender = "Мужской" if gender_raw == "Male" else "Женский" if gender_raw == "Female" else gender_raw
        gender = sanitize_for_excel(gender)
        
        phone = sanitize_for_excel(profile.get("phone_number", "—"))
        username = sanitize_for_excel(profile.get("telegram_username", "—"))
        arrival = c.get("arrival_time") or "—"
        departure = c.get("departure_time") or "—"
        
        # Расчет времени
        hours = "—"
        if arrival != "—" and departure != "—":
            try:
                # Очистка времени на случай лишних пробелов или спецсимволов
                arrival_clean = arrival.strip()
                departure_clean = departure.strip()
                
                fmt = "%H:%M"
                t1 = datetime.strptime(arrival_clean, fmt)
                t2 = datetime.strptime(departure_clean, fmt)
                delta = t2 - t1
                # Если уход на следующий день (редко, но бывает)
                if delta.total_seconds() < 0:
                    hours = round((delta.total_seconds() + 86400) / 3600, 2)
                else:
                    hours = round(delta.total_seconds() / 3600, 2)
            except Exception:
                hours = 0

        # Вставляем данные
        ws.append([full_name, gender, phone, username, arrival, departure, hours, default_rate, ""])
        
        # Добавляем формулу для подсчета (H - ставка, G - часы)
        if isinstance(hours, (int, float)) and hours > 0:
            ws[f"I{row_idx}"] = f"=G{row_idx}*H{row_idx}"
        else:
            ws[f"I{row_idx}"] = 0
            
        row_idx += 1

    # Авто-ширина колонок
    for i, col in enumerate(ws.columns, 1):
        max_length = 0
        column = ws.cell(row=2, column=i).column_letter  # Берем букву колонки из шапки (2-я строка)
        for cell in col:
            try:
                val = str(cell.value) if cell.value is not None else ""
                if len(val) > max_length:
                    max_length = len(val)
            except:
                pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    # Сохранение
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"event_data_{timestamp}.xlsx"
    # Используем /tmp/ или текущую директорию если /tmp/ нет (на Windows это может быть проблема, но в этой среде обычно есть)
    filepath = os.path.join(os.getcwd(), filename)
    wb.save(filepath)
    return filepath
