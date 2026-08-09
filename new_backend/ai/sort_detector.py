from typing import Optional, Dict

from new_backend.ai.query_utils import QueryUtils


class SortDetector:

    @staticmethod
    def detect_sort(query: str) -> Optional[Dict[str, str]]:

        q = QueryUtils.normalize_query(query)

        # -----------------------------------
        # Is this actually a sort request?
        # -----------------------------------

        sort_keywords = [
            "sort",
            "order",
            "arrange"
        ]

        if not any(k in q for k in sort_keywords):
            return None

        # -----------------------------------
        # Order
        # -----------------------------------

        order = "asc"

        if any(word in q for word in [
            "descending",
            "desc",
            "highest",
            "largest",
            "biggest",
            "reverse",
            "z to a"
        ]):
            order = "desc"

        # -----------------------------------
        # CRM Field Mapping
        # -----------------------------------

        field_map = {

            "name": "Name",
            "names": "Name",

            "company": "Company",

            "amount": "Amount",

            "annual revenue": "Annual_Revenue",
            "revenue": "Annual_Revenue",

            "industry": "Industry",

            "stage": "Stage",

            "status": "Lead_Status",

            "email": "Email",

            "phone": "Phone",

            "mobile": "Phone",

            "city": "City",

            "created": "Created_Time",
            "created date": "Created_Time",

            "closing date": "Closing_Date"
        }

        for key, crm_field in field_map.items():

            if key in q:

                return {
                    "field": crm_field,
                    "order": order
                }

        return None