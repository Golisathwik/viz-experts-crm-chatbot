import json
import os
from typing import Any, Dict, List, Optional
from collections import Counter
from new_backend.services.analytics_engine import AnalyticsEngine


class VisualizationEngine:
    """
    V2 Visualization Engine

    Responsibilities:
    - Generate tables
    - Generate chart configurations
    - Generate KPI cards
    - Assemble frontend response

    Does NOT:
    - Call CRM
    - Call LLM
    """

    def __init__(self):

        self.rules = {}

        rules_path = os.path.join(
            os.path.dirname(__file__),
            "analytics_rules.json",
        )

        if os.path.exists(rules_path):

            with open(
                rules_path,
                "r",
                encoding="utf-8",
            ) as f:

                self.rules = json.load(f)

    # ----------------------------------------------------
    # Helpers
    # ----------------------------------------------------

    @staticmethod
    def get_value(column: str, record: Dict[str, Any]):

        if not isinstance(record, dict):
            return ""

        aliases = {
            "name": [
                "Full_Name",
                "Name",
                "Lead_Name",
                "Deal_Name",
                "Account_Name",
            ],

            "company": [
                "Company",
            ],

            "phone": [
                "Phone",
                "Mobile",
            ],

            "email": [
                "Email",
            ],

            "lead status": [
                "Lead_Status",
            ],

            "account name": [
                "Account_Name",
            ],

            "industry": [
                "Industry",
            ],

            "website": [
                "Website",
            ],

            "amount": [
                "Amount",
            ],

            "revenue": [
                "Annual_Revenue",
            ],

            "closing date": [
                "Closing_Date",
            ],
        }

        key = column.lower()

        if key in aliases:

            for candidate in aliases[key]:
                if candidate in record and record[candidate] not in ("", None):
                    return record[candidate]
                
        if "First_Name" in record or "Last_Name" in record:

            if key == "name":

                return (
                    f"{record.get('First_Name','')} "
                    f"{record.get('Last_Name','')}"
                ).strip()
            
        if column == "Module":
            return record.get("_module", "")

        normalized = (
            column.lower()
            .replace(" ", "")
            .replace("_", "")
        )

        for k, v in record.items():

            nk = (
                k.lower()
                .replace(" ", "")
                .replace("_", "")
            )

            if normalized == nk or normalized in nk:

                if isinstance(v, dict):

                    return (
                        v.get("name")
                        or v.get("value")
                        or str(v)
                    )

                return v

        return ""

    @staticmethod
    def default_columns(module: str, sample: Dict):

        mapping = {
            "Leads": [
                "Full_Name",
                "Company",
                "Phone",
                "Email",
                "Lead Status",
            ],
            "Contacts": [
                "Name",
                "Email",
                "Phone",
                "Account Name",
            ],
            "Deals": [
                "Deal Name",
                "Stage",
                "Amount",
                "Closing Date",
            ],
            "Accounts": [
                "Account Name",
                "Industry",
                "Phone",
                "Website",
            ],
        }

        if module in mapping:
            return mapping[module]

        cols = []

        for k in sample.keys():

            if (
                "$" in k
                or "Owner" in k
                or "Approval" in k
                or "Image" in k
            ):
                continue

            cols.append(k)

            if len(cols) == 5:
                break

        return cols
    
    
    def count_by_field(self, records, field):

        counter = Counter()

        for record in records:

            value = record.get(field)

            if isinstance(value, dict):
                value = value.get("name")

            if not value:
                value = "Unknown"

            counter[str(value)] += 1

        return {
            "labels": list(counter.keys()),
            "values": list(counter.values())
        }
    # ----------------------------------------------------
    # Table
    # ----------------------------------------------------

    def build_table(
        self,
        module,
        records,
        columns=None,
        title=None,
        understanding=None,
    ):

        if not records:
            return None

        # --------------------------------------------------
        # Determine table columns
        # --------------------------------------------------

        # Global Search ALWAYS uses the common cross-module columns.
        # Do not allow LLM-requested table_columns to override this.
        if module == "Global Search":

            columns = [
                "Name",
                "Company",
                "Phone",
                "Email",
                "Module",
            ]

        elif not columns:

            columns = self.default_columns(
                module,
                records[0],
            )

            # ----------------------------
            # Dynamic Filter Column
            # ----------------------------

            if understanding and understanding.get("filter"):

                field = understanding["filter"].get("field")

                if field:

                    field = field.replace("_", " ")

                    if field not in columns:
                        columns.append(field)

            # ----------------------------
            # Dynamic Sort Column
            # ----------------------------

            if understanding and understanding.get("sort"):

                field = understanding["sort"].get("field")

                if field:

                    field = field.replace("_", " ")

                    if field not in columns:
                        columns.append(field)

            # Remove duplicates
            columns = list(dict.fromkeys(columns))

            # Limit columns
            columns = columns[:6]
                
        # --------------------------------------------------
        # Serial Number
        # --------------------------------------------------

                
        columns = ["S.No"] + columns

        rows = []

        for index, record in enumerate(records, start=1):

            rows.append(
                [
                    index
                ] + [
                    self.get_value(col, record)
                    for col in columns[1:]
                ]
            )

        return {
            "type": "table",
            "title": title or f"{module} List",
            "columns": columns,
            "rows": rows,
        }

    # ----------------------------------------------------
    # Charts
    # ----------------------------------------------------

    def build_chart(
        self,
        chart_type: str,
        title: str,
        labels: List,
        values: List,
    ):

        return {
            "type": chart_type,
            "title": title,
            "labels": labels,
            "values": values,
        }
          
        

    # ----------------------------------------------------
    # KPI Cards
    # ----------------------------------------------------

    def build_kpis(
        self,
        records: List[Dict],
        module: str,
    ):

        return AnalyticsEngine.generate_kpis(
            records,
            module,
        )
        
    def build_dashboard(
        self,
        module: str,
        records: List[Dict],
    ):

        if not records:
            return None

        dashboard = {
            "type": "dashboard",
            "module": module,
            "charts": []
        }

        charts = AnalyticsEngine.build_dashboard_data(
            module=module,
            records=records,
        )

        for chart in charts:

            dashboard["charts"].append(
                chart["chart"]
            )

        return dashboard

    # ----------------------------------------------------
    # Final Response
    # ----------------------------------------------------

    @staticmethod
    def assemble_response(
        summary: str,
        table=None,
        chart=None,
        kpis=None,
        suggestions=None,
    ):

        return {
            "summary": summary,
            "table": table,
            "chart": chart,
            "kpis": kpis,
            "suggestions": suggestions or [],
        }