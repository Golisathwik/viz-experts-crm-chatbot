from typing import Dict

from new_backend.services.filter_service import (
    FilterService,
    FIELD_MAPPING,
)
class SortService:
    @staticmethod
    def apply_sort(records: list, module: str, sort_def: Dict[str, str]) -> list:
        if not records or not sort_def:
            return records
        print("MODULE =", module)
        print("SORT DEF =", sort_def)
        print("TOTAL RECORDS =", len(records))
        mapping = FIELD_MAPPING.get(module, {})

        user_field = sort_def.get("field")
        order = sort_def.get("order", "asc")

        field = mapping.get(user_field.lower(), user_field)
        print("FIELD MAPPING =", mapping)
        print("USER FIELD =", user_field)
        print("FINAL FIELD =", field)
        reverse = order == "desc"

        def sort_key(record):
            value = record.get(field)

            if isinstance(value, dict):
                value = value.get("name", "")

            # Numeric fields
            if field in ["Amount", "Annual_Revenue"]:
                try:
                    return float(value or 0)
                except Exception:
                    return 0.0

            # Date fields
            if field in ["Created_Time", "Closing_Date"]:
                d = FilterService.parse_record_date(value)
                if d:
                    return d.toordinal()
                return 0

            # Everything else -> string
            return str(value or "").lower()

        sorted_records = sorted(records, key=sort_key, reverse=reverse)

        print("[SORT FIELD]", field)

        for i, rec in enumerate(sorted_records[:5]):
            print(
                f"[SORT RESULT {i+1}]",
                rec.get("Full_Name") or rec.get("Account_Name") or rec.get("Deal_Name"),
                rec.get(field)
            )

        return sorted_records