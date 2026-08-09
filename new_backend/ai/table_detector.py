from typing import List
import re

class TableDetector:

    @staticmethod
    def detect_table_columns(query: str, module: str) -> list[str]:

        q = query.lower()
        tokens = re.findall(r"\b\w+\b", q)

        field_map = {

            "Leads": {
                "name": "Full_Name",
                "names": "Full_Name",
                "company": "Company",
                "companies": "Company",
                "email": "Email",
                "emails": "Email",
                "phone": "Phone",
                "phones": "Phone",
                "mobile": "Mobile",
                "mobiles": "Mobile",
                "status": "Lead_Status",
                "source": "Lead_Source",
                "owner": "Owner",
                "revenue": "Annual_Revenue",
            },

            "Contacts": {
                "name": "Full_Name",
                "names": "Full_Name",
                "email": "Email",
                "emails": "Email",
                "phone": "Phone",
                "phones": "Phone",
                "mobile": "Mobile",
                "city": "Mailing_City",
                "title": "Title",
            },

            "Accounts": {
                "name": "Account_Name",
                "names": "Account_Name",
                "industry": "Industry",
                "website": "Website",
                "phone": "Phone",
                "phones": "Phone",
                "revenue": "Annual_Revenue",
            },

            "Deals": {
                "name": "Deal_Name",
                "names": "Deal_Name",
                "amount": "Amount",
                "stage": "Stage",
                "owner": "Owner",
                "closing": "Closing_Date",
            },
        }

        defaults = {

            "Leads": [
                "Full_Name",
                "Company",
                "Phone",
                "Email",
                "Lead_Status",
            ],

            "Contacts": [
                "Full_Name",
                "Email",
                "Phone",
                "Account_Name",
            ],

            "Accounts": [
                "Account_Name",
                "Industry",
                "Phone",
                "Website",
            ],

            "Deals": [
                "Deal_Name",
                "Stage",
                "Amount",
                "Closing_Date",
            ],
        }

        mapping = field_map.get(module, {})

        columns = []

        field_requested = False

        for keyword, field in mapping.items():

            if keyword in tokens or keyword in q:

                field_requested = True

                if field not in columns:
                    columns.append(field)

        # User didn't ask for any fields → return default table
        if not field_requested:
            return defaults.get(module, [])

        # Always include primary identifier
        primary = {
            "Leads": "Full_Name",
            "Contacts": "Full_Name",
            "Accounts": "Account_Name",
            "Deals": "Deal_Name",
        }.get(module)

        if primary and primary not in columns:
            columns.insert(0, primary)

        return columns