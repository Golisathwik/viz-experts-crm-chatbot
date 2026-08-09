import re
from typing import Optional, Dict


class CreateDetector:

    @staticmethod
    def extract_create_details(query: str) -> Optional[Dict]:

        q = query.lower().strip()

        module_keywords = {
            "Leads": [
                "lead",
                "leads",
            ],
            "Contacts": [
                "contact",
                "contacts",
            ],
            "Accounts": [
                "account",
                "accounts",
                "company",
            ],
            "Deals": [
                "deal",
                "deals",
                "opportunity",
                "opportunities",
            ],
        }

        create_words = [
            "create",
            "add",
            "new",
            "register",
        ]

        # Must contain a create word
        if not any(word in q for word in create_words):
            return None

        # Find the CRM module
        for module, keywords in module_keywords.items():

            if any(keyword in q for keyword in keywords):

                return {
                    "module": module,
                    "raw_text": query.strip(),
                }

        return None