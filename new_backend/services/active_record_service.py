"""
active_record_service.py

Maintains the currently selected CRM record
for follow-up conversations.

Uses CacheService instead of the database.
"""

from typing import Optional, Dict, Any

from new_backend.services.cache_service import CacheService


class ActiveRecordService:

    @staticmethod
    def set_active_record(
        session_id: int,
        module: str,
        record_id: str,
        record_name: str,
        record: Optional[Dict[str, Any]] = None,
    ):

        state = CacheService.get_state(session_id)

        state["current_module"] = module
        state["selected_record_id"] = record_id
        state["selected_record"] = record_name
        state["selected_record_data"] = record or {}

    @staticmethod
    def get_active_record(session_id: int):

        state = CacheService.get_state(session_id)

        if not state.get("selected_record_id"):
            return None

        return {
            "module": state.get("current_module"),
            "record_id": state.get("selected_record_id"),
            "record_name": state.get("selected_record"),
            "record": state.get("selected_record_data"),
        }

    @staticmethod
    def clear_active_record(session_id: int):

        state = CacheService.get_state(session_id)

        state["selected_record"] = None
        state["selected_record_id"] = None
        state["selected_record_data"] = {}

    @staticmethod
    def has_active_record(session_id: int) -> bool:

        state = CacheService.get_state(session_id)

        return state.get("selected_record_id") is not None