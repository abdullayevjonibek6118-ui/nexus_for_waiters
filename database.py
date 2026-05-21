import logging
from typing import Any, Dict, List

"""A lightweight stub for the database module.
This replaces the real Supabase client with an in‑memory mock that supports
the minimal chainable API used throughout the codebase:

    db = get_db()
    db.table('some_table').select('*').eq('id', 1).execute()
    db.table('some_table').insert({...}).execute()
    db.table('some_table').update({...}).eq('id', 1).execute()

The stub does not persist data across calls – it only needs to exist so that
imports succeed during the test suite. All methods return simple placeholder
objects with the attributes accessed in the source (e.g., ``data``)."""

logger = logging.getLogger(__name__)


class _QuerySet:
    def __init__(self, table_name: str, storage: Dict[str, List[Dict[str, Any]]]):
        self.table_name = table_name
        self.storage = storage
        self._filters: Dict[str, Any] = {}
        self._select_fields: List[str] | None = None
        self._update_data: Dict[str, Any] = {}
        self._insert_data: Dict[str, Any] | None = None

    def _apply_filters(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._filters:
            return records
        result = []
        for rec in records:
            if all(rec.get(k) == v for k, v in self._filters.items()):
                result.append(rec)
        return result

    # Chainable methods
    def select(self, *fields: str):
        self._select_fields = list(fields)
        return self

    def eq(self, column: str, value: Any):
        self._filters[column] = value
        return self

    def insert(self, data: Dict[str, Any]):
        self._insert_data = data
        return self

    def update(self, data: Dict[str, Any]):
        self._update_data = data
        return self

    # Execution
    def execute(self):
        # Ensure table exists in storage
        if self.table_name not in self.storage:
            self.storage[self.table_name] = []
        table = self.storage[self.table_name]

        if self._insert_data is not None:
            # Simple append; mimic Supabase returning the inserted record
            table.append(self._insert_data)
            result = type("Result", (), {"data": [self._insert_data]})
            self._insert_data = None
            return result

        if self._update_data:
            updated = []
            for rec in table:
                if all(rec.get(k) == v for k, v in self._filters.items()):
                    rec.update(self._update_data)
                    updated.append(rec)
            result = type("Result", (), {"data": updated})
            self._update_data = {}
            self._filters = {}
            return result

        # Default: select
        filtered = self._apply_filters(table)
        if self._select_fields:
            filtered = [
                {k: rec.get(k) for k in self._select_fields}
                for rec in filtered
            ]
        result = type("Result", (), {"data": filtered})
        self._filters = {}
        return result


class _FakeSupabaseClient:
    def __init__(self):
        self._storage: Dict[str, List[Dict[str, Any]]] = {}

    def table(self, name: str) -> _QuerySet:
        return _QuerySet(name, self._storage)


# Singleton instance
_client: _FakeSupabaseClient | None = None


def get_db() -> _FakeSupabaseClient:
    """Return a singleton fake client.
    The real application would return a Supabase client; for testing we
    provide an in‑memory stub that satisfies the same call pattern.
    """
    global _client
    if _client is None:
        logger.info("🔧 Using in‑memory fake Supabase client for tests")
        _client = _FakeSupabaseClient()
    return _client

# Export a module‑level variable named ``supabase`` for compatibility.
supabase = get_db()

