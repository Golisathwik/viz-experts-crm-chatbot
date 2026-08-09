from math import ceil
from typing import Dict, Any, List

from new_backend.services.cache_service import CacheService


class PaginationService:
    """
    Central pagination service.

    Responsibilities:
        • Slice cached records
        • Maintain current page
        • Maintain navigation window
        • Return pagination metadata

    This service never builds tables, summaries or charts.
    ReadService is responsible for presentation.
    """

    @staticmethod
    def paginate(
        session_id: int,
        records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        state = CacheService.get_state(session_id)

        if records is None:
            records = []

        total_records = len(records)
        state["total_records"] = total_records

        page_size = max(1, state.get("page_size", 10))

        # ---------------------------------------------
        # Window navigation (first/last/next/previous N)
        # ---------------------------------------------
        if "window_start" in state:

            start = max(0, state.get("window_start", 0))

            count = state.get("window_count", page_size)

            end = min(start + count, total_records)

            page_records = records[start:end]

            current_page = (start // page_size) + 1

            total_pages = max(1, ceil(total_records / page_size))

            state["current_page"] = current_page

            return {
                "records": page_records,
                "pagination": {
                    "page": current_page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                    "total_records": total_records,
                    "start": start + 1 if total_records else 0,
                    "end": end,
                    "has_next": end < total_records,
                    "has_previous": start > 0,
                },
            }

        # ---------------------------------------------
        # Standard page navigation
        # ---------------------------------------------
        current_page = state.get("current_page", 1)

        total_pages = max(1, ceil(total_records / page_size))

        current_page = max(
            1,
            min(current_page, total_pages),
        )

        state["current_page"] = current_page

        start = (current_page - 1) * page_size

        end = min(start + page_size, total_records)

        page_records = records[start:end]

        return {
            "records": page_records,
            "pagination": {
                "page": current_page,
                "page_size": page_size,
                "total_pages": total_pages,
                "total_records": total_records,
                "start": start + 1 if total_records else 0,
                "end": end,
                "has_next": current_page < total_pages,
                "has_previous": current_page > 1,
            },
        }

    @staticmethod
    def reset(session_id: int):

        state = CacheService.get_state(session_id)

        state["current_page"] = 1
        state["window_start"] = 0
        state["window_count"] = state.get("page_size", 10)

    @staticmethod
    def next_page(session_id: int):

        state = CacheService.get_state(session_id)

        state["current_page"] += 1

    @staticmethod
    def previous_page(session_id: int):

        state = CacheService.get_state(session_id)

        if state["current_page"] > 1:
            state["current_page"] -= 1

    @staticmethod
    def goto_page(
        session_id: int,
        page: int,
    ):

        state = CacheService.get_state(session_id)

        state["current_page"] = max(1, page)

    @staticmethod
    def get_metadata(session_id: int) -> Dict[str, Any]:

        state = CacheService.get_state(session_id)

        page_size = state.get("page_size", 10)

        total_records = state.get("total_records", 0)

        total_pages = max(1, ceil(total_records / page_size))

        return {
            "page": state.get("current_page", 1),
            "page_size": page_size,
            "total_pages": total_pages,
            "total_records": total_records,
        }