"""
Nexus AI — Database client.

Production uses the real Supabase client configured through ``config.settings``.
For isolated local tests, set ``NEXUS_FAKE_DB=1`` to use the in-memory
Supabase-like stub below.
"""
import logging
import os
from typing import Any, Dict, List

from supabase import Client, create_client

logger = logging.getLogger(__name__)


class _QuerySet:
    def __init__(self, table_name: str, storage: Dict[str, List[Dict[str, Any]]]):
        self.table_name = table_name
        self.storage = storage
        self._eq_filters: Dict[str, Any] = {}
        self._neq_filters: Dict[str, Any] = {}
        self._in_filters: Dict[str, set[Any]] = {}
        self._select_fields: List[str] | None = None
        self._update_data: Dict[str, Any] = {}
        self._insert_data: Dict[str, Any] | List[Dict[str, Any]] | None = None
        self._upsert_data: Dict[str, Any] | List[Dict[str, Any]] | None = None
        self._order_column: str | None = None
        self._order_desc = False
        self._limit: int | None = None
        self._single = False

    def _apply_filters(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for rec in records:
            if any(rec.get(k) != v for k, v in self._eq_filters.items()):
                continue
            if any(rec.get(k) == v for k, v in self._neq_filters.items()):
                continue
            if any(rec.get(k) not in values for k, values in self._in_filters.items()):
                continue
            result.append(rec)
        return result

    def select(self, *fields: str):
        self._select_fields = list(fields)
        return self

    def eq(self, column: str, value: Any):
        self._eq_filters[column] = value
        return self

    def neq(self, column: str, value: Any):
        self._neq_filters[column] = value
        return self

    def in_(self, column: str, values: List[Any]):
        self._in_filters[column] = set(values)
        return self

    def order(self, column: str, desc: bool = False):
        self._order_column = column
        self._order_desc = desc
        return self

    def limit(self, count: int):
        self._limit = count
        return self

    def single(self):
        self._single = True
        return self

    def insert(self, data: Dict[str, Any] | List[Dict[str, Any]]):
        self._insert_data = data
        return self

    def upsert(self, data: Dict[str, Any] | List[Dict[str, Any]]):
        self._upsert_data = data
        return self

    def update(self, data: Dict[str, Any]):
        self._update_data = data
        return self

    def _project(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._select_fields or self._select_fields == ["*"]:
            return records
        # Keep full records for relationship/select expressions that the fake DB
        # cannot faithfully emulate, e.g. "*, candidates(*)".
        if any("(" in field or field == "*" for field in self._select_fields):
            return records
        fields = [field.strip() for raw in self._select_fields for field in raw.split(",")]
        return [{k: rec.get(k) for k in fields} for rec in records]

    def execute(self):
        table = self.storage.setdefault(self.table_name, [])

        if self._insert_data is not None:
            records = self._insert_data if isinstance(self._insert_data, list) else [self._insert_data]
            table.extend(records)
            return type("Result", (), {"data": records})

        if self._upsert_data is not None:
            records = self._upsert_data if isinstance(self._upsert_data, list) else [self._upsert_data]
            upserted = []
            key_fields = ("id", "event_id", "user_id")
            for record in records:
                existing = None
                for rec in table:
                    comparable = [key for key in key_fields if key in record and key in rec]
                    if comparable and all(rec[key] == record[key] for key in comparable):
                        existing = rec
                        break
                if existing is None:
                    table.append(record)
                    upserted.append(record)
                else:
                    existing.update(record)
                    upserted.append(existing)
            return type("Result", (), {"data": upserted})

        if self._update_data:
            updated = []
            for rec in self._apply_filters(table):
                rec.update(self._update_data)
                updated.append(rec)
            return type("Result", (), {"data": updated})

        filtered = self._apply_filters(table)
        if self._order_column:
            filtered = sorted(
                filtered,
                key=lambda rec: (rec.get(self._order_column) is None, rec.get(self._order_column)),
                reverse=self._order_desc,
            )
        if self._limit is not None:
            filtered = filtered[: self._limit]
        projected = self._project(filtered)
        data = (projected[0] if projected else None) if self._single else projected
        return type("Result", (), {"data": data})


class _FakeSupabaseClient:
    def __init__(self):
        self._storage: Dict[str, List[Dict[str, Any]]] = {}

    def table(self, name: str) -> _QuerySet:
        return _QuerySet(name, self._storage)


_client: Client | _FakeSupabaseClient | None = None


def get_db() -> Client | _FakeSupabaseClient:
    """Return a singleton Supabase client or an opt-in in-memory test stub."""
    global _client
    if _client is None:
        if os.getenv("NEXUS_FAKE_DB", "").lower() in {"1", "true", "yes"}:
            logger.info("🔧 Using in-memory fake Supabase client")
            _client = _FakeSupabaseClient()
        else:
            from config import settings

            _client = create_client(settings.supabase_url, settings.supabase_key)
            logger.info("✅ Supabase client initialized")
    return _client


supabase = get_db()
