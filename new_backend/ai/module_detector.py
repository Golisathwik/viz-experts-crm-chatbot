import re
from typing import Optional
from new_backend.ai.query_utils import QueryUtils


class ModuleDetector:

    @staticmethod
    def detect_module(query: str) -> Optional[str]:
        q = QueryUtils.normalize_query(query)

        module_patterns = {
            "Leads": [
                "lead",
                "leads"
            ],
            "Contacts": [
                "contact",
                "contacts"
            ],
            "Accounts": [
                "account",
                "accounts",
                "company",
                "companies"
            ],
            "Deals": [
                "deal",
                "deals",
                "opportunity",
                "opportunities"
            ],
            "Activities": [
                "activity",
                "activities",
                "task",
                "tasks",
                "meeting",
                "meetings",
                "call",
                "calls"
            ]
        }

        for module, keywords in module_patterns.items():
            if any(re.search(rf"\b{re.escape(keyword)}\b", q) for keyword in keywords):
                return module

        return None