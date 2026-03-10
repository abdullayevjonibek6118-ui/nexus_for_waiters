Nexus AI Personal AI Agent, [04.03.2026 14:49]
Отлично, Жони. Ниже полный, унифицированный обзор проекта Nexus AI в формате “что мы делаем, как это работает под капотом и какие сценарии используют ваши пользователи”. Я разделю материал на ключевые разделы: цель проекта, архитектура, доменная модель, технические стеки, интеграции и данные, рабочие сценарии пользователей, процессы, безопасность и комплаенс, тестирование, релизы и дорожная карта, а также детали для операционной деятельности и мониторинга.

1. Цель проекта

• Nexus AI — это B2B SaaS-платформа для интеллектуального сорсинга и управления наймом, ориентированная на SMB, стартапы, HR-агентства и HR-департаменты технологических компаний.
• Основная ценность: сокращение времени найма, снижение расходов на подбор и повышение качества кандидатов через автоматизацию рутинных HR-процессов и повышение предсказуемости результатов.

2. Архитектура (high-level)

• Service-based архитектура с четким разделением ролей:
  • EventRSVP-Backend (центральный оркестратор): управление жизненным циклом мероприятия, голосованием, подбором кандидатов, назначением времени и генерацией данных для Sheet. Основной бизнес-оркестр.
  • TelegramBotManager (тонкий транспорт): интеграция с Telegram API, обработка входящих событий, нормализация данных, идемпотентность, ретраи, публикация опросов и отправка приватных сообщений.
  • CandidateProfileManager (Supabase): хранение профилей кандидатов и event-специфических данных (EventCandidate), поддержка запросов и обновлений.
  • Spreadsheet-Creator (Google Sheets): создание и заполнение Google Sheets по событию.
  • Scheduler: администрирование напоминаний и отложенных задач (например, 14-дневное напоминание об оплате).
  • ValidationLayer: валидаторы входных данных (Pydantic/Zod) для контракта API и входящих сообщений.
  • AuditLogger: журнал аудита (event_logs) для трассировки действий и изменений.
• Коммуникационный поток:
  • TelegramBotManager принимает входящие обновления, нормализует и передает в EventRSVP-Backend.
  • EventRSVP-Backend координирует работу с CandidateProfileManager, Spreadsheet-Creator и Scheduler, записывает логи в event_logs.
  • Все данные, связанные с кандидатом на уровне события (arrival_time, departure_time, vote_status, selected) хранятся в EventCandidate (связующая таблица между Event и Candidate). Поля candidate_profile (ФИО, телефон) берутся из CandidateProfileManager или резервного источника по необходимости.
• Непрерывная интеграция и развёртывание (CI/CD) обеспечивают Production-ready инфраструктуру: мониторинг, логирование, трассировка, откликающиеся сервисы.

3. Доменная модель (ключевые сущности)

• Event
  • event_id (PK)
  • title
  • date
  • location
  • max_candidates
  • status (Draft, Poll_Published, Recruiting, Selection_Completed, Times_Assigned, Sheet_Generated, Candidates_Confirmed, Completed, Payment_Pending, Closed)
  • poll_id
• Candidate
  • user_id (PK) — Telegram user_id
  • first_name
  • last_name
  • phone_number
  • telegram_username
  • has_messaged_bot
  • created_at
  • (Дополнительно: рейтинг/кэш для скорости доступа)
• EventCandidate (связующая таблица между Event и Candidate)
  • event_id (FK -> Event)
  • user_id (FK -> Candidate)
  • vote_status (yes/no/maybe)
  • selected (bool)
  • arrival_time (time, ISO 24h)
  • departure_time (time, ISO 24h)
  • confirmed (bool)
• event_logs (Audit)
  • log_id (PK)
  • event_id
  • action
  • performed_by
  • timestamp
  • details (json)
• Дополнительно
  • has_messaged_bot (флаг на CandidateProfileManager) — хотя основной флаг и данные хранятся в EventCandidate
  • sheet_url (URL Google Sheet) в состоянии Sheet_Generated
  • reminder_status в Scheduler (для отслеживания оплаты)

4. Технологический стек (рекомендации)

• Backend: Node.js или Python (FastAPI/Express) — для EventRSVP-Backend, с модульной архитектурой и чётко отделенной бизнес-логикой.

Nexus AI Personal AI Agent, [04.03.2026 14:49]
• Telegram Bot: Telegram Bot API (webhooks или long polling), Go или Python – для TelegramBotManager, с поддержкой идемпотентности и rate-limiting.
• База данных: Supabase (PostgreSQL) как источник данных кандидатов; отдельные таблицы Event, EventCandidate, кандидаты и связки.
• Google Sheets: Google Sheets API v4, таблицы создаются динамически по событию и заполняются данными.
• Валидация: Pydantic (Python) или Zod (TypeScript) — для контракта входящих данных, схем проверки и валидности.
• Асинхронность и планирование задач: Redis + Bull (Node) или Celery (Python) + cron-like планировщики для Scheduler.
• Безопасность и аудит: строгий контроль доступа, псевдонимизация PII, аудит изменений в event_logs.
• Инфраструктура: Docker/K8s для деплоймента, инфраструктура как код (Terraform/CloudFormation) и мониторинг (Prometheus + Grafana, ELK/OpenSearch).

5. API контракты и ключевые точки интеграции

• TelegramBotManager
  • handle_incoming_message(update_data) -> normalized_payload
  • send_group_poll(chat_id, question, options, is_anonymous=false, allows_multiple_answers=false, close_date) -> poll_id
  • send_private_message(user_id, text, reply_markup, parse_mode) -> message_id
  • get_chat_member_contact(chat_id, user_id) -> {name, phone}
  • get_bot_dialog_history(user_id) -> message_history
• EventRSVP-Backend
  • process_telegram_update(update_data) -> actions for TelegramBotManager
  • create_event_poll(recruiter_id, chat_id, event_details) -> event_id, poll_id
  • handle_poll_vote_results(poll_id, votes_data) -> selected_candidate_ids
  • initiate_candidate_contact(candidate_user_id, event_context) -> messaging_instructions
  • collect_times_from_recruiter(event_id, selected_candidate_ids) -> {candidate_user_id: arrival_time, departure_time}
  • finalize_event_data_for_sheet(event_id, candidate_time_data) -> sheet_data
  • confirm_candidate_participation(candidate_user_id, event_details, recruiter_times) -> status
• CandidateProfileManager
  • get_candidate_profile(user_id) -> CandidateProfile
  • update_candidate_profile(user_id, data) -> status
  • create_candidate_profile(user_data) -> status
  • get_candidates_by_event_selection(user_ids) -> [CandidateProfile]
• Spreadsheet-Creator
  • create_and_populate_sheet(event_name, sheet_data) -> {sheet_id, sheet_url}
  • get_sheet_url_format() -> string
• Scheduler
  • schedule_payment_reminder(event_id, due_date) -> job_id
  • on_payment_confirmed(event_id) -> status
• ValidationLayer (optional)
  • Validators for inputs: validate_event_details, validate_candidate_data, validate_times, etc.
• AuditLogger (optional)
  • log_event(event_id, action, performed_by, details)

6. User Scenarios (end-to-end flow)

• US_REC_1 (Recruiter): создание мероприятия и опроса
  • Рекрутер задаёт детали мероприятия через admin-панель: дата, место, лимит.
  • EventRSVP-Backend вызывает TelegramBotManager.send_group_poll для группового чата.
  • Poll публикуется; poll_id сохраняется в Event.
  • Статус мероприятия — Draft, затем Poll_Published после публикации.
• US_REC_2 (Recruiter): голосование и выбор кандидатов
  • Кандидаты голосуют в групповом чате (poll_vote).
  • TelegramBotManager передаёт vote_data в EventRSVP-Backend.
  • EventRSVP-Backend формирует список голосовавших и помечает selected для выбранных (через команды /select в админ-панели или внутри бота).
  • Статус обновляется к Selection_Completed.
• US_REC_3 (Recruiter): назначение времени приезда/ухода
  • Рекрутер через админ-панель/бота указывает arrival_time и departure_time для выбранных кандидатов.
  • EventRSVP-Backend валидирует форматы (ISO 24h), сохраняет в EventCandidate.
  • Когда все времена заполнены, статус переходит в Times_Assigned.
• US_REC_4 (Recruiter): создание Google Sheet
  • После назначения времен система вызывает Spreadsheet-Creator.create_and_populate_sheet с данными кандидатов и временем.

Nexus AI Personal AI Agent, [04.03.2026 14:49]
• Sheets API создаёт таблицу с названием "<дата> - <место>", колонками: ФИО, Номер телефона, Время приезда, Время ухода.
  • sheet_url сохраняется в Sheet_Generated и прикрепляется к Event.
• US_REC_5 (Recruiter): подтверждение кандидатам
  • Бот отправляет приватное сообщение каждому выбранному кандидату с деталями мероприятия и формирования статуса подтверждения.
  • Кандидат получает инструкции и может подтвердить участие.
• US_CAND_1 (Candidate): голосование в опросе
  • Кандидат видит опрос и выбирает вариант (да/нет/интересен).
  • Результат голосования фиксируется в EventRSVP-Backend.
• US_CAND_2 (Candidate): инициирование диалога
  • Если кандидат голосовал и выбран, бот инициирует приватный диалог для сбора данных или инструкций.
  • Кандидат может ответить через чат; данные попадают в CandidateProfileManager/EventCandidate.
• US_CAND_3 (Candidate): получение подтверждения
  • Кандидат получает приватное подтверждение об участии вместе с деталями (место, дата, время).
  • При подтверждении статус обновляется; данные для Sheet и уведомления синхронизируются.

7. Безопасность, комплаенс и требования к качеству

• Идемпотентность: каждый Telegram update содержит update_id; ведётся таблица processed_updates для предотвращения повторной обработки.
• Rate limiting и retry: ограничение частоты обращений к Telegram API; автоматизированная повторная отправка в случае ошибок.
• Конфиденциальность: данные кандидатов и события обрабатываются в контексте конкретного мероприятия; персональные данные (PII) минимизируются и защищаются (псевдонимизация, доступ по ролям).
• Аудит: запись всех ключевых действий в event_logs; возможность трассировки изменений и возврата к исходным данным.
• Распознавание ошибок: детальные сообщения об ошибках и автоматическая эскалация в случае критических сбоев.

8. Тестирование и качество

• Виды тестов:
  • Юнит тесты для валидаторов и контрактов каждого субагента.
  • Интеграционные тесты: End-to-End тестирование сценариев US_REC_1→US_REC_5 и US_CAND_1→US_CAND_3.
  • Контрактные тесты между EventRSVP-Backend и TelegramBotManager, CandidateProfileManager, Spreadsheet-Creator.
  • Нагрузочные тесты на голосование и создание Sheets.
• Моки и стабы: заглушки Supabase и Google Sheets для локального тестирования; тестовые учетные записи Telegram в тест-аккаунтах.
• Метрики: time-to-publish-poll, time-to-select, time-to-times-assigned, accuracy of alignment (CV-to-vacancy), time-to-create-sheet, number of successful confirmations, payment-reminder reliability.

9. Релизы и дорожная карта

• MVP-версия:
  • Основной цикл: создание мероприятия → публикация опроса → сбор голосов → выбор кандидатов → назначение времен → создание Google Sheet → уведомление кандидатов → подтверждения.
  • Базовая интеграция Supabase и Google Sheets.
  • Встроенные проверки и аудит.
• Расширение:
  • Добавление AI-скоринга и рейтингов кандидатов, триггеров для явок/неявок, прогнозирования просрочек.
  • Расширение GTM и интеграции с ATS/HRIS.
  • Партнерства и дополнительные источники данных.

10. Как мы будем двигаться дальше (практически)

• Шаг 1: Разделить на файлы и начать задавать дизайн-файлы (у нас уже есть набор US_REC_1…US_REC_5 и US_CAND_1…US_CAND_3).
• Шаг 2: Развернуть спецификации субагентов в виде детальных контрактов (API, параметры, ответы, примеры payloads).
• Шаг 3: Определить и зафиксировать схемы данных в Supabase (Event, EventCandidate, Candidate).
• Шаг 4: Определить спецификацию Google Sheets и пример итогового листа.
• Шаг 5: Подготовить MVP-план разработки и расписать этапы внедрения.
• Шаг 6: Создать набор тест-кейсов и окружения для локального/интеграционного тестирования.

Как хочется двигаться дальше

• Могу сразу подготовить:

Nexus AI Personal AI Agent, [04.03.2026 14:49]
• Полный набор спецификаций субагентов в виде отдельных markdown‑файлов (например: Subagent_TelegramBotManager.md, Subagent_EventRSVP_Backend.md, Subagent_CandidateProfileManager.md, Subagent_SpreadsheetCreator.md, Subagent_Scheduler.md, Subagent_ValidationLayer.md, Subagent_AuditLogger.md).
  • Раскладывание API контрактов в отдельный файл API_Contracts.md с примерами payloads.
  • Дорожную карту MVP в формате MVP_Plan.md, включая критерии готовности и метрики.
  • Схемы данных в виде Schema_EventModel.md, Schema_Supabase_Candidates.md, Schema_GoogleSheets.md.
  • Пример User Flows (User Flow Diagrams) в виде текстовых описаний и ссылок на потенциальные изображения/модели.

Формат выдачи

• Могу выдать именно в виде отдельных markdown-файлов, готовых к добавлению в репозиторий, и затем выгружать их как набор документов или конвертировать в PDF по запросу.
• Также могу включить маленькие примеры payloads и сценариев тестирования прямо в каждый файл.

Предпочитаешь сразу получить набор первых 6 markdown-файлов с названиями:

• Subagent_TelegramBotManager.md
• Subagent_EventRSVP_Backend.md
• Subagent_CandidateProfileManager.md
• Subagent_SpreadsheetCreator.md
• Subagent_Scheduler.md
• Subagent_ValidationLayer.md

Или хочешь чуть иного порядка сделать структуру файлов? Сообщи, в каком формате тебе удобнее получить и какие именно потенциальные примеры payloads включать в контент файлов.