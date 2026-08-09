from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class CacheService:
    """
    Central cache service for conversation state.

    This replaces the global cache from the old project while
    keeping the same cache structure.
    """

    _cache: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def initialize_state(cls, session_id: int) -> Dict[str, Any]:

        return cls._cache.setdefault(
            session_id,
            {
                "current_module": None,
                "current_filters": {},
                "current_sort": None,

                "page_size": 10,
                "current_page": 1,
                "total_records": 0,

                "cached_dataset": [],
                "raw_cached_dataset": [],

                "module_cache": {},
                "raw_module_cache": {},

                "visualization_state": {},

                "timestamp": None,

                "intent": None,
                "query": None,
                "query_term": None,
                "raw_query": None,

                "pending_disambiguation": None,
                "pending_filter_clarification": None,

                # New architecture additions
                "selected_record": None,
                "selected_record_id": None,
                
                "pending_record_selection": None,
                "pending_records": [],
                "pending_module": None,
                "conversation_context": {},
                "analytics_result": None,
                "chart_result": None,
                "table_result": None,
            },
        )

    @classmethod
    def get_state(cls, session_id: int) -> Dict[str, Any]:
        return cls.initialize_state(session_id)

    @classmethod
    def is_cache_valid(cls, session_id: int, module: str) -> bool:

        state = cls.get_state(session_id)

        if state["current_module"] != module:
            return False

        if not state["raw_cached_dataset"]:
            return False

        timestamp = state.get("timestamp")

        if timestamp is None:
            return False

        return datetime.now() - timestamp <= timedelta(minutes=5)

    @classmethod
    def update_cache(
        cls,
        session_id: int,
        module: str,
        records,
        raw_records,
        intent,
        query,
        query_term,
    ):

        state = cls.get_state(session_id)

        state["cached_dataset"] = list(records) if records else []
        state["raw_cached_dataset"] = list(raw_records) if raw_records else []

        state["current_module"] = module
        state["total_records"] = len(records) if records else 0

        state["timestamp"] = datetime.now()

        state["intent"] = intent
        state["query"] = query
        state["query_term"] = query_term
        state["raw_query"] = query

        state["current_page"] = 1

        # Navigation state
        state["window_start"] = 0
        state["window_count"] = state["page_size"]

        state["visualization_state"] = {}

        state.setdefault("module_cache", {})[module] = list(records) if records else []
        state.setdefault("raw_module_cache", {})[module] = list(raw_records) if raw_records else []

    @classmethod
    def clear_module_cache(cls, session_id: int):

        state = cls.get_state(session_id)

        state["cached_dataset"] = []
        state["raw_cached_dataset"] = []

        state["current_module"] = None
        state["current_filters"] = {}
        state["current_sort"] = None

        state["total_records"] = 0
        state["timestamp"] = None
        state["window_start"] = 0
        state["window_count"] = state["page_size"]

        state["intent"] = None
        state["query"] = None
        state["query_term"] = None
        state["raw_query"] = None

        cls.reset_pagination(session_id)

    @classmethod
    def clear_all_cache(cls, session_id: int):
        cls._cache.pop(session_id, None)

    @classmethod
    def reset_pagination(cls, session_id: int):

        state = cls.get_state(session_id)

        state["current_page"] = 1
        state["visualization_state"] = {}