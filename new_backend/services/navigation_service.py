import re
from typing import Dict, Any, Optional

from new_backend.services.cache_service import CacheService
from new_backend.services.active_record_service import ActiveRecordService


class NavigationService:

    @staticmethod
    def is_navigation_query(query: str) -> bool:

        q = query.lower().strip()

        patterns = [

            r"^(?:show\s+)?first\s+\d+$",
            r"^(?:show\s+)?last\s+\d+$",

            r"^(?:show\s+)?record\s+\d+$",
            r"^(?:show\s+)?records?\s+\d+\s+(?:to|-)\s+\d+$",
        ]

        return any(re.match(p, q) for p in patterns)

    @staticmethod
    def handle(session_id: int, query: str) -> Optional[Dict[str, Any]]:

        state = CacheService.get_state(session_id)

        if not state["cached_dataset"]:
            return None

        q = query.lower().strip()

        # ---------- SHOW FIRST ----------
        m = re.match(r"^(?:show\s+)?first\s+(\d+)$", q)
        if m:

            count = int(m.group(1))

            state["window_start"] = 0
            state["window_count"] = count

            return NavigationService.current_window(session_id)

        # ---------- LAST ----------
        m = re.match(r"^(?:show\s+)?last\s+(\d+)$", q)
        if m:

            count = int(m.group(1))

            total = len(state["cached_dataset"])

            state["window_start"] = max(
                0,
                total - count,
            )

            state["window_count"] = count

            return NavigationService.current_window(session_id)
        
        # ---------- RECORD RANGE ----------

        m = re.match(
            r"^(?:show\s+)?records?\s+(\d+)\s+(?:to|-)\s+(\d+)$",
            q,
        )

        if m:

            start = max(1, int(m.group(1)))
            end = max(start, int(m.group(2)))

            records = state["cached_dataset"]

            start_index = start - 1
            end_index = min(end, len(records))

            return {
                "navigation": "range",
                "start": start,
                "end": end_index,
                "total": len(records),
                "records": records[start_index:end_index],
            }

        # ---------- RECORD ----------
        m = re.match(r"^(?:show\s+)?record\s+(\d+)$", q)

        if m:

            idx = int(m.group(1)) - 1

            records = state["cached_dataset"]

            if idx < 0 or idx >= len(records):
                return None

            record = records[idx]

            ActiveRecordService.set_active_record(
                session_id=session_id,
                module=state["current_module"],
                record_id=str(record.get("id")),
                record_name=record.get(
                    "Full_Name",
                    record.get(
                        "Company",
                        record.get(
                            "Account_Name",
                            record.get("Deal_Name", ""),
                        ),
                    ),
                ),
                record=record,
            )

            return {
                "navigation": "record",
                "record": record,
            }

        return None

    @staticmethod
    def current_window(session_id: int):

        state = CacheService.get_state(session_id)

        start = state.get("window_start", 0)

        count = state.get(
            "window_count",
            state["page_size"],
        )

        end = start + count

        return {
            "navigation": "page",
            "start": start + 1,
            "end": min(end, len(state["cached_dataset"])),
            "total": len(state["cached_dataset"]),
            "records": state["cached_dataset"][start:end],
        }