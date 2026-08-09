import re
from typing import Optional, Dict


class DeleteDetector:

    @staticmethod
    def extract_delete_details(query: str) -> Optional[Dict]:

        p = query.strip()

        if p.endswith("."):
            p = p[:-1].strip()

        # -------------------------------------------------
        # 1. Current / Selected record
        # -------------------------------------------------

        current_pattern = (
            r"^(?:delete|remove)\s+"
            r"(this|it|current|selected)"
            r"(?:\s+(?:record|lead|contact|account|deal))?$"
        )

        m = re.match(current_pattern, p, re.IGNORECASE)

        if m:
            return {
                "target_record": "this record",
                "module": None,
            }

        # -------------------------------------------------
        # 2. Module + Record
        # -------------------------------------------------

        pattern1 = (
            r"^(?:delete|remove)\s+"
            r"(lead|contact|account|deal|leads|contacts|accounts|deals)\s+"
            r"(.+)$"
        )

        m = re.match(pattern1, p, re.IGNORECASE)

        if m:

            module, target_record = m.groups()

            module_map = {
                "lead": "Leads",
                "leads": "Leads",
                "contact": "Contacts",
                "contacts": "Contacts",
                "account": "Accounts",
                "accounts": "Accounts",
                "deal": "Deals",
                "deals": "Deals",
            }

            return {
                "target_record": target_record.strip(),
                "module": module_map[module.lower()],
            }

        # -------------------------------------------------
        # 3. Generic delete
        # -------------------------------------------------

        pattern2 = (
            r"^(?:delete|remove)\s+(.+)$"
        )

        m = re.match(pattern2, p, re.IGNORECASE)

        if m:

            return {
                "target_record": m.group(1).strip(),
                "module": None,
            }

        return None