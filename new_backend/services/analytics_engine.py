from datetime import datetime
from typing import Any, Dict, List, Optional


class AnalyticsEngine:
    """
    Analytics Engine

    Responsibilities:
    - Compute KPI statistics
    - Group data
    - Aggregate values
    - Prepare chart-ready datasets

    Does NOT:
    - Call CRM
    - Call LLM
    - Access database
    """

    @staticmethod
    def get_numeric_value(record: Dict[str, Any], field: str) -> float:
        if not isinstance(record, dict):
            return 0.0

        value = record.get(field)

        if value in (None, ""):
            return 0.0

        try:
            if isinstance(value, str):
                value = value.replace(",", "").replace("₹", "").strip()
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def compute_basic_stats(
        records: List[Dict[str, Any]],
        module: str,
    ) -> Dict[str, Any]:

        total = len(records)

        if total == 0:
            return {
                "total_records": 0,
                "summary": "No records found."
            }

        stats = {
            "total_records": total
        }

        # ---------------- LEADS ----------------

        if module == "Leads":

            status = {}

            industries = {}

            for record in records:

                s = record.get("Lead_Status") or record.get("Status") or "Unknown"

                status[s] = status.get(s, 0) + 1

                ind = record.get("Industry")

                if ind:
                    industries[ind] = industries.get(ind, 0) + 1

            stats["status_distribution"] = status

            stats["top_industries"] = dict(
                sorted(
                    industries.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
            )

        # ---------------- DEALS ----------------

        elif module == "Deals":

            revenue = 0.0

            stages = {}

            for record in records:

                revenue += AnalyticsEngine.get_numeric_value(
                    record,
                    "Amount",
                )

                stage = record.get("Stage") or "Unknown"

                stages[stage] = stages.get(stage, 0) + 1

            stats["total_revenue"] = revenue

            stats["average_revenue"] = round(revenue / total, 2)

            stats["stage_distribution"] = stages

            won = stages.get("Closed Won", 0)

            stats["conversion_rate"] = round(
                (won / total) * 100,
                2,
            )

        # ---------------- CONTACTS ----------------

        elif module == "Contacts":

            sources = {}

            for record in records:

                src = record.get("Lead_Source") or "Unknown"

                sources[src] = sources.get(src, 0) + 1

            stats["source_distribution"] = sources

        # ---------------- ACCOUNTS ----------------

        elif module == "Accounts":

            revenue = 0.0

            industries = {}

            for record in records:

                revenue += AnalyticsEngine.get_numeric_value(
                    record,
                    "Annual_Revenue",
                )

                ind = record.get("Industry")

                if ind:
                    industries[ind] = industries.get(ind, 0) + 1

            stats["total_revenue"] = revenue

            stats["top_industries"] = dict(
                sorted(
                    industries.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
            )

        return stats

    @staticmethod
    def aggregate_grouped_data(
        records: List[Dict[str, Any]],
        group_by: str,
        agg_type: str = "count",
        calc_field: Optional[str] = None,
    ) -> Dict[str, List]:

        grouped = {}

        for record in records:
            FIELD_MAPPING = {
                "Owner": "Owner_Name",
                "Owner Name": "Owner_Name",

                "Created By": "Created_By_Name",
                "Modified By": "Modified_By_Name",

                "Account": "Account_Name",
                "Contact": "Contact_Name",

                "Industry": "Industry",
                "Stage": "Stage",
                "Lead Status": "Lead_Status",
            }

            field_name = FIELD_MAPPING.get(group_by, group_by)
            value = record.get(field_name)

            if isinstance(value, dict):
                value = (
                    value.get("name")
                    or value.get("full_name")
                    or value.get("value")
                    or value.get("display_value")
                )
                
            # Handle missing values

            is_date_field = (
                group_by is not None and any(
                    x in group_by.lower()
                    for x in [
                        "date",
                        "created_time",
                        "created time",
                        "modified_time",
                        "modified time",
                        "closing_date",
                        "closing date",
                    ]
                )
            )

            if is_date_field:

                # Skip records that don't have a date
                if value in (None, "", "Unknown"):
                    continue

            else:

                if value is None:
                    value = "Unknown"

            if value is None:
                value = "Unknown"

            if group_by is not None and any(
                x in group_by.lower()
                for x in [
                    "date",
                    "created_time",
                    "created time",
                    "modified_time",
                    "modified time",
                    "closing_date",
                    "closing date",
                ]
            ):

                try:

                    date_value = datetime.fromisoformat(
                        str(value).split("T")[0]
                    )

                    # collect all valid dates
                    all_dates = []

                    for r in records:

                        d = r.get(field_name)

                        if d:

                            try:
                                all_dates.append(
                                    datetime.fromisoformat(
                                        str(d).split("T")[0]
                                    )
                                )
                            except Exception:
                                pass

                    if len(all_dates) >= 2:

                        span = (max(all_dates) - min(all_dates)).days

                        if span <= 31:

                            value = date_value.strftime("%d %b")

                        elif span <= 365:

                            value = date_value.strftime("%b %Y")

                        else:

                            value = date_value.strftime("%Y")

                    else:

                        value = date_value.strftime("%d %b")

                except Exception:
                    pass

            grouped.setdefault(str(value), []).append(record)

        labels = []

        values = []

        for label, items in grouped.items():

            labels.append(label)

            if agg_type == "count":

                values.append(len(items))

            elif agg_type == "sum":

                values.append(
                    sum(
                        AnalyticsEngine.get_numeric_value(
                            x,
                            calc_field,
                        )
                        for x in items
                    )
                )

            elif agg_type == "avg":

                nums = [
                    AnalyticsEngine.get_numeric_value(
                        x,
                        calc_field,
                    )
                    for x in items
                ]

                values.append(
                    sum(nums) / len(nums)
                    if nums else 0
                )

            else:

                values.append(len(items))

        if is_date_field:

            try:

                pairs = sorted(
                    zip(labels, values),
                    key=lambda x: datetime.strptime(
                        x[0],
                        "%d %b"
                    )
                    if len(x[0]) <= 6
                    else datetime.strptime(
                        x[0],
                        "%b %Y"
                    )
                    if len(x[0]) <= 8
                    else datetime.strptime(
                        x[0],
                        "%Y"
                    )
                )

            except Exception:

                pairs = list(zip(labels, values))

        else:

            pairs = sorted(
                zip(labels, values),
                key=lambda x: x[1],
                reverse=True,
            )

        if pairs:
            labels, values = zip(*pairs)
        else:
            labels, values = (), ()

        return {
            "labels": list(labels),
            "values": list(values),
        }

    @staticmethod
    def generate_kpis(
        records: List[Dict[str, Any]],
        module: str,
    ) -> Dict[str, Any]:
        records = records or []

        stats = AnalyticsEngine.compute_basic_stats(
            records,
            module,
        )

        # ---------------- LEADS ----------------

        if module == "Leads":

            status = stats.get("status_distribution", {})

            return {
                "module": module,
                "total_leads": stats.get("total_records", 0),
                "contacted": status.get("Contacted", 0),
                "qualified": status.get("Qualified", 0),
                "junk": status.get("Junk Lead", 0),
                "lost": status.get("Lost Lead", 0),
                "top_industries": stats.get("top_industries", {}),
            }

        # ---------------- DEALS ----------------

        elif module == "Deals":

            stages = stats.get("stage_distribution", {})

            return {
                "module": module,
                "total_deals": stats.get("total_records", 0),
                "won": stages.get("Closed Won", 0),
                "lost": stages.get("Closed Lost", 0),
                "pipeline_value": stats.get("total_revenue", 0),
                "average_deal": stats.get("average_revenue", 0),
                "conversion_rate": stats.get("conversion_rate", 0),
            }

        # ---------------- CONTACTS ----------------

        elif module == "Contacts":

            return {
                "module": module,
                "total_contacts": stats.get("total_records", 0),
                "top_sources": stats.get(
                    "source_distribution",
                    {},
                ),
            }

        # ---------------- ACCOUNTS ----------------

        elif module == "Accounts":

            return {
                "module": module,
                "total_accounts": stats.get("total_records", 0),
                "total_revenue": stats.get("total_revenue", 0),
                "top_industries": stats.get(
                    "top_industries",
                    {},
                ),
            }

        return {
            "module": module,
            "record_count": stats.get("total_records", 0),
        }
        
    @staticmethod
    def process(
        module: str,
        records: List[Dict[str, Any]],
        analytics_request: Dict[str, Any],
    ) -> Dict[str, Any]:

        group_by = analytics_request.get("group_by")
        aggregation = analytics_request.get("aggregation", "count")
        metric = analytics_request.get("metric")
        chart = analytics_request.get("chart", "bar")
        if not group_by:
            return {
                "summary": "I couldn't determine how to group the data. Please specify something like 'by stage', 'by owner', or 'by industry'.",

                "chart": {
                    "type": "bar",
                    "title": "",
                    "labels": [],
                    "values": [],
                },

                "labels": [],
                "values": [],

                "table": {
                    "columns": [],
                    "rows": []
                },

                "kpis": AnalyticsEngine.generate_kpis(
                    records,
                    module,
                ),
            }

        grouped = AnalyticsEngine.aggregate_grouped_data(
            records=records,
            group_by=group_by,
            agg_type=aggregation,
            calc_field=metric,
        )
        if aggregation == "avg":
            grouped["values"] = [
                round(v, 2) if isinstance(v, (int, float)) else v
                for v in grouped["values"]
            ]

        if aggregation == "count":
            title = f"Count by {group_by}"
        else:
            title = f"{aggregation.title()} of {metric or 'Records'} by {group_by}"
        # Auto select chart if LLM didn't specify one

        if not chart:

            label_count = len(grouped["labels"])

            # Trend questions
            if group_by.lower() in [
                "created time",
                "created_time",
                "closing date",
                "closing_date",
                "modified time",
                "modified_time"
            ]:
                chart = "line"

            # Small category distribution
            elif label_count <= 6:
                chart = "pie"

            # Default
            else:
                chart = "bar"
                
        # If only one time bucket exists,
        # a bar chart is clearer than a single-point line chart.

        if chart == "line" and len(grouped["labels"]) <= 1:

            chart = "bar"
        return {
            "summary": title,

            "chart": {
                "type": chart,
                "orientation": "horizontal" if max(
                    (len(str(x)) for x in grouped["labels"]),
                    default=0
                ) > 12 else "vertical",
                "title": title,
                "labels": grouped["labels"],
                "values": grouped["values"],
            },

            "labels": grouped["labels"],
            "values": grouped["values"],

            "table": {
                "columns": [group_by, aggregation],
                "rows": list(zip(grouped["labels"], grouped["values"]))
            },

            "kpis": AnalyticsEngine.generate_kpis(
                records,
                module,
            ),
        }
        
        
    @staticmethod
    def build_dashboard_data(module: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Returns the predefined dashboard charts for each CRM module.
        """

        if not records:
            return []

        dashboards = {
            "Leads": [
                {
                    "group_by": "Lead Status",
                    "aggregation": "count",
                    "chart": "pie",
                },
                {
                    "group_by": "Lead_Source",
                    "aggregation": "count",
                    "chart": "bar",
                },
                {
                    "group_by": "Created_Time",
                    "aggregation": "count",
                    "chart": "line",
                },
            ],

            "Deals": [
                {
                    "group_by": "Stage",
                    "aggregation": "count",
                    "chart": "pie",
                },
                {
                    "group_by": "Stage",
                    "aggregation": "sum",
                    "metric": "Amount",
                    "chart": "bar",
                },
                {
                    "group_by": "Closing_Date",
                    "aggregation": "sum",
                    "metric": "Amount",
                    "chart": "line",
                },
            ],

            "Accounts": [
                {
                    "group_by": "Industry",
                    "aggregation": "count",
                    "chart": "bar",
                },
                {
                    "group_by": "Industry",
                    "aggregation": "sum",
                    "metric": "Annual_Revenue",
                    "chart": "pie",
                },
                {
                    "group_by": "Account_Name",
                    "aggregation": "sum",
                    "metric": "Annual_Revenue",
                    "chart": "bar",
                },
            ],

            "Contacts": [
                {
                    "group_by": "Owner",
                    "aggregation": "count",
                    "chart": "bar",
                },
                {
                    "group_by": "Department",
                    "aggregation": "count",
                    "chart": "pie",
                },
                {
                    "group_by": "Created_Time",
                    "aggregation": "count",
                    "chart": "line",
                },
            ],
        }

        charts = []

        for request in dashboards.get(module, []):
            charts.append(
                AnalyticsEngine.process(
                    module=module,
                    records=records,
                    analytics_request=request,
                )
            )

        return charts