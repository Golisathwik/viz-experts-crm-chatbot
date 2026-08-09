import re
from typing import Optional, Dict, Any


class VisualizationDetector:

    CHART_KEYWORDS = [
        "chart",
        "graph",
        "dashboard",
        "analytics",
        "analysis",
        "report",
        "summary",
        "statistics",
        "stats",
        "distribution",
        "trend",
        "pie",
        "bar",
        "line",
    ]

    GROUP_BY_RULES = {
        "status": "Lead_Status",
        "industry": "Industry",
        "source": "Lead_Source",
        "owner": "Owner",
        "stage": "Stage",
        "month": "Created_Time",
        "date": "Created_Time",
        "year": "Created_Time",
    }

    @staticmethod
    def detect_visualization(query: str) -> Optional[Dict[str, Any]]:

        q = query.lower()

        if not any(word in q for word in VisualizationDetector.CHART_KEYWORDS):
            return None

        chart_type = "bar"

        if "pie" in q:
            chart_type = "pie"

        elif "line" in q:
            chart_type = "line"

        elif "dashboard" in q:
            chart_type = "dashboard"

        elif "summary" in q:
            chart_type = "summary"

        group_by = None

        for key, value in VisualizationDetector.GROUP_BY_RULES.items():
            if re.search(rf"\b{re.escape(key)}\b", q):
                group_by = value
                break

        return {
            "requires_visualization": True,
            "chart_type": chart_type,
            "group_by": group_by,
        }