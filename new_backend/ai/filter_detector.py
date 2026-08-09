import re
from typing import Optional
from dateutil.parser import parse


class FilterDetector:
    @staticmethod
    def parse_numeric_value(value: str) -> float:
        value = value.lower().replace(",", "").strip()

        m = re.match(
            r"(\d+(?:\.\d+)?)\s*(k|m|b|lac|lacs|lakh|lakhs|crore|crores)?",
            value
        )

        if not m:
            return float(value)

        number = float(m.group(1))
        unit = m.group(2)

        multipliers = {
            "k": 1_000,
            "m": 1_000_000,
            "b": 1_000_000_000,
            "lac": 100_000,
            "lacs": 100_000,
            "lakh": 100_000,
            "lakhs": 100_000,
            "crore": 10_000_000,
            "crores": 10_000_000,
        }

        if unit:
            number *= multipliers[unit]

        return number

    @staticmethod
    def detect_filter(query: str):

        q = query.lower()

        result = {}

        # -----------------------------
        # Detect field
        # -----------------------------

        field_patterns = {

            "Lead_Status": ["lead status", "status"],

            "Stage": ["stage"],

            "Industry": ["industry"],

            "Department": ["department"],

            "Amount": ["amount", "deal amount", "price"],

            "Annual_Revenue": ["annual revenue", "revenue"],

            "Closing_Date": ["closing date", "closing"],

            "Company": ["company", "business", "organization"],

            "Account_Name": ["account"],

            "Deal_Name": ["deal"],

            "Owner": ["owner"],

            "Email": ["email", "gmail"],

            "Phone": ["phone", "mobile", "number"],

            "Full_Name": ["name"]

        }

        for field, keywords in field_patterns.items():
            if any(k in q for k in keywords):
                result["field"] = field
                break

        # -----------------------------
        # STRING OPERATORS
        # -----------------------------

        # starts with / begins with
        m = re.search(
            r"(?:starts?\s+with|starting\s+with|begins?\s+with|beginning\s+with)\s+(?:the\s+)?(?:letter\s+)?['\"]?([a-z0-9@._\-\s]+)['\"]?$",
            q
        )

        if m and "field" in result:

            result["operator"] = "starts_with"
            result["values"] = [m.group(1).strip()]
            return result


        # ends with
        m = re.search(
            r"(?:ends?\s+with|ending\s+with)\s+['\"]?([a-z0-9@._\-\s]+)['\"]?$",
            q
        )

        if m and "field" in result:

            result["operator"] = "ends_with"
            result["values"] = [m.group(1).strip()]
            return result


        # contains
        m = re.search(
            r"(?:contains?|containing)\s+['\"]?(.+?)['\"]?$",
            q
        )

        if m and "field" in result:

            result["operator"] = "contains"
            result["values"] = [m.group(1).strip()]
            return result


        # equals / is
        m = re.search(
            r"(?:is|=|equals?)\s+['\"]?(.+?)['\"]?$",
            q
        )

        if m and "field" in result:

            result["operator"] = "equals"
            result["values"] = [m.group(1).strip()]
            return result

        # -----------------------------
        # BETWEEN
        # -----------------------------

        m = re.search(
            r"(?:amount|annual revenue|revenue|deal amount)?\s*"
            r"(?:between|from)\s*"
            r"([\d.,]+\s*(?:k|m|b|lac|lacs|lakh|lakhs|crore|crores)?)"
            r"\s*(?:and|to|-)\s*"
            r"([\d.,]+\s*(?:k|m|b|lac|lacs|lakh|lakhs|crore|crores)?)",
            q
        )

        if m:

            if "field" not in result:

                if "deal" in q:
                    result["field"] = "Amount"

                elif "account" in q:
                    result["field"] = "Annual_Revenue"

                elif "lead" in q:
                    result["field"] = "Annual_Revenue"

                else:
                    result["field"] = "Amount"

            result["operator"] = "between"

            result["values"] = [
                FilterDetector.parse_numeric_value(m.group(1)),
                FilterDetector.parse_numeric_value(m.group(2))
            ]

            return result
        # -----------------------------
        # GREATER THAN
        # -----------------------------

        m = re.search(
            r"(?:greater than|above|over|>)\s*([\d.,]+\s*(?:k|m|b|lac|lacs|lakh|lakhs|crore|crores)?)",
            q
        )

        if m:

            result["operator"] = "greater_than"
            result["values"] = [
                FilterDetector.parse_numeric_value(m.group(1))
            ]
            return result

        # -----------------------------
        # LESS THAN
        # -----------------------------

        m = re.search(
            r"(?:less than|below|under|<)\s*([\d.,]+\s*(?:k|m|b|lac|lacs|lakh|lakhs|crore|crores)?)",
            q
        )

        if m:

            result["operator"] = "less_than"
            result["values"] = [
                FilterDetector.parse_numeric_value(m.group(1))
            ]
            return result
        
        # -----------------------------
        # AFTER DATE
        # -----------------------------

        m = re.search(r"after\s+(.+)$", q)

        if m:

            try:
                parsed = parse(m.group(1), dayfirst=True).date()

                result["operator"] = "after"
                result["values"] = [parsed]

                return result

            except Exception:
                pass

        # -----------------------------
        # BEFORE DATE
        # -----------------------------

        m = re.search(r"before\s+(.+)$", q)

        if m:

            try:
                parsed = parse(m.group(1), dayfirst=True).date()

                result["operator"] = "before"
                result["values"] = [parsed]

                return result

            except Exception:
                pass

        return None


    @staticmethod
    def has_filter_keywords(query: str):

        q = query.lower()

        keywords = [
            "filter",
            "where",
            "is",
            "starts with",
            "starting with",
            "begins with",
            "beginning with",
            "ends with",
            "ending with",
            "contains",
            "containing",
            "=",
            ">",
            "<",
            ">=",
            "<=",
            "between",
            "after",
            "before",
            "greater than",
            "less than",
        ]

        return any(k in q for k in keywords)