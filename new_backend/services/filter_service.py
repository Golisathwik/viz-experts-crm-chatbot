import re
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any
from new_backend.ai.query_understanding import QueryUnderstanding

FIELD_MAPPING = {
    "Deals": {
        "deal name": "Deal_Name",
        "name": "Deal_Name",
        "amount": "Amount",
        "stage": "Stage",
        "closing date": "Closing_Date",
        "date": "Closing_Date",
        "account name": "Account_Name",
        "account": "Account_Name"
    },
    "Leads": {
        "first name": "First_Name",
        "last name": "Last_Name",
        "full name": "Full_Name",
        "name": "Full_Name",
        "company": "Company",
        "email": "Email",
        "phone": "Phone",
        "annual revenue": "Annual_Revenue",
        "revenue": "Annual_Revenue",
        "status": "Lead_Status",
        "lead status": "Lead_Status"
    },
    "Contacts": {
        "full name": "Full_Name",
        "name": "Full_Name",
        "email": "Email",
        "phone": "Phone",
        "mailing city": "Mailing_City",
        "city": "Mailing_City"
    },
    "Accounts": {
        "account name": "Account_Name",
        "name": "Account_Name",
        "company": "Account_Name",
        "industry": "Industry",
        "website": "Website",
        "annual revenue": "Annual_Revenue",
        "revenue": "Annual_Revenue",
        "phone": "Phone"
    }
}

DEFAULT_FIELDS = {
    "Deals": {
        "numeric": "Amount",
        "date": "Closing_Date",
        "string": "Deal_Name"
    },
    "Leads": {
        "numeric": "Annual_Revenue",
        "date": "Created_Time",
        "string": "Full_Name"
    },
    "Contacts": {
        "numeric": None,
        "date": "Created_Time",
        "string": "Full_Name"
    },
    "Accounts": {
        "numeric": "Annual_Revenue",
        "date": "Created_Time",
        "string": "Account_Name"
    }
}
class FilterService:
    
    @staticmethod
    def normalize_query(query: str) -> str:
        """Normalize user queries for equivalent terminology before parsing."""
        q = query.lower().strip()
        
        # 1. Normalize comparison operators (compound first to prevent partial matches)
        q = re.sub(r"\bgreater\s+than\s+or\s+equal\s+to\b", "greater than or equal to", q)
        q = re.sub(r"\babove\s+or\s+equal\s+to\b", "greater than or equal to", q)
        q = re.sub(r"\bmore\s+than\s+or\s+equal\s+to\b", "greater than or equal to", q)
        q = re.sub(r"\b(?:above|more\s+than|over)\b", "greater than", q)
        
        q = re.sub(r"\bless\s+than\s+or\s+equal\s+to\b", "less than or equal to", q)
        q = re.sub(r"\bbelow\s+or\s+equal\s+to\b", "less than or equal to", q)
        q = re.sub(r"\bunder\s+or\s+equal\s+to\b", "less than or equal to", q)
        q = re.sub(r"\b(?:below|under)\b", "less than", q)
        
        q = re.sub(r"\bnot\s+equal\s+to\b", "not equals", q)
        q = re.sub(r"\bnot\s+equals\b", "not equals", q)
        q = re.sub(r"\bequal\s+to\b", "equals", q)
        
        # 2. Normalize field synonyms
        q = re.sub(r"\b(?:deal\s+amount|deal\s+value|value)\b", "amount", q)
        q = re.sub(r"\b(?:organization|business)\b", "company", q)

        # --------------------------------------------------
        # Normalize natural string filter phrases
        # --------------------------------------------------

        # starts with the letter B -> starts with B
        q = re.sub(
            r"\bstarts?\s+with\s+(?:the\s+)?letter\s+([a-z0-9])\b",
            r"starts with \1",
            q
        )

        # begins with A -> starts with A
        q = re.sub(
            r"\bbegins?\s+with\b",
            "starts with",
            q
        )

        # beginning with A -> starting with A
        q = re.sub(
            r"\bbeginning\s+with\b",
            "starting with",
            q
        )

        # begin with A -> start with A
        q = re.sub(
            r"\bbegin\s+with\b",
            "start with",
            q
        )

        # start with A -> starts with A
        q = re.sub(
            r"\bstart\s+with\b",
            "starts with",
            q
        )

        # ending with X -> ends with X
        q = re.sub(
            r"\bending\s+with\b",
            "ends with",
            q
        )

        # end with X -> ends with X
        q = re.sub(
            r"\bend\s+with\b",
            "ends with",
            q
        )

        # contain -> contains
        q = re.sub(
            r"\bcontain\b",
            "contains",
            q
        )

        # containing -> contains
        q = re.sub(
            r"\bcontaining\b",
            "contains",
            q
        )

        return q
    

    @staticmethod
    def parse_number_value(val_str: str) -> Optional[float]:
        """Parse numeric strings, handling suffixes like 'k', 'lakh', 'lakhs' and symbols like '₹'."""
        val_str = val_str.lower().strip()
        multiplier = 1.0
        if "lakh" in val_str:
            multiplier = 100000.0
            val_str = val_str.replace("lakhs", "").replace("lakh", "").strip()
        elif "k" in val_str:
            multiplier = 1000.0
            val_str = val_str.replace("k", "").strip()
            
        # Remove currency symbols and commas
        val_str = val_str.replace("₹", "").replace("$", "").replace(",", "")
        # Remove any non-numeric characters except digits and dots
        val_str = re.sub(r"[^\d\.]", "", val_str)
        if not val_str:
            return None
        try:
            return float(val_str) * multiplier
        except ValueError:
            return None

    @staticmethod
    def parse_date_value(val_str: str) -> Optional[date]:
        """Parse absolute date string into a date object."""
        val_str = val_str.lower().strip()
        
        # Check for ISO format like 2026-06-04
        iso_match = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", val_str)
        if iso_match:
            try:
                return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
            except ValueError:
                pass
                
        # Try day-month-year or day-month (e.g. 04-06-2026 or 04-06)
        dm_match = re.search(r"\b(\d{1,2})[-/](\d{1,2})\b(?:[-/](\d{4}))?", val_str)
        if dm_match:
            try:
                day = int(dm_match.group(1))
                month = int(dm_match.group(2))
                year = int(dm_match.group(3)) if dm_match.group(3) else 2026
                return date(year, month, day)
            except ValueError:
                pass

        # Try word-based day + month: 4th June, 4 June, june 4th, june 4
        MONTHS = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        }
        
        # pattern: 4th june / 4 june
        d_m_match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b", val_str)
        if d_m_match:
            try:
                day = int(d_m_match.group(1))
                month = MONTHS[d_m_match.group(2)]
                year = 2026  # default year
                return date(year, month, day)
            except ValueError:
                pass
                
        # pattern: june 4th / june 4
        m_d_match = re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})(?:st|nd|rd|th)?\b", val_str)
        if m_d_match:
            try:
                month = MONTHS[m_d_match.group(1)]
                day = int(m_d_match.group(2))
                year = 2026
                return date(year, month, day)
            except ValueError:
                pass

        # pattern: january / june (month only)
        month_match = re.search(r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b", val_str)
        if month_match:
            try:
                month = MONTHS[month_match.group(1)]
                return date(2026, month, 1)
            except ValueError:
                pass
                
        return None

    @staticmethod
    def parse_record_date(val) -> Optional[date]:
        """Parse record date field into date object."""
        if not val:
            return None
        val_str = str(val).strip()
        if "t" in val_str.lower():
            val_str = val_str.lower().split("t")[0]
        elif " " in val_str:
            val_str = val_str.split(" ")[0]
        try:
            parts = re.split(r"[-/]", val_str)
            if len(parts) >= 3:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            pass
        return None

    @staticmethod
    def parse_filter_query(query: str, module: str) -> Optional[Dict[str, Any]]:
        """
        Parse a normalized user query for deterministic filters.
        """
        q_lower = query.lower().strip()
        mapping = FIELD_MAPPING.get(module)
        if not mapping:
            return None
            
        # Helpers to resolve field name (explicit mapped key or module default)
        def resolve_field(explicit_key: str, val_type: str) -> str:
            if explicit_key in mapping:
                return mapping[explicit_key]
            return DEFAULT_FIELDS.get(module, {}).get(val_type)

        # 1. Date Filters
        current_date = datetime.now().date()
        
        # Check relative terms first
        if "last month" in q_lower:
            field_name = "Created_Time" if ("created" in q_lower or module != "Deals") else "Closing_Date"
            if current_date.month == 1:
                start = date(current_date.year - 1, 12, 1)
                end = date(current_date.year, 1, 1) - timedelta(days=1)
            else:
                start = date(current_date.year, current_date.month - 1, 1)
                end = date(current_date.year, current_date.month, 1) - timedelta(days=1)
            return {"field": field_name, "operator": "date_between", "values": [start, end]}
            
        if "this month" in q_lower:
            field_name = "Created_Time" if ("created" in q_lower or module != "Deals") else "Closing_Date"
            start = date(current_date.year, current_date.month, 1)
            if current_date.month == 12:
                next_month = date(current_date.year + 1, 1, 1)
            else:
                next_month = date(current_date.year, current_date.month + 1, 1)
            end = next_month - timedelta(days=1)
            return {"field": field_name, "operator": "date_between", "values": [start, end]}

        if "last week" in q_lower:
            field_name = "Created_Time" if ("created" in q_lower or module != "Deals") else "Closing_Date"
            start = current_date - timedelta(days=current_date.weekday() + 7)
            end = start + timedelta(days=6)
            return {"field": field_name, "operator": "date_between", "values": [start, end]}

        if "this week" in q_lower:
            field_name = "Created_Time" if ("created" in q_lower or module != "Deals") else "Closing_Date"
            start = current_date - timedelta(days=current_date.weekday())
            end = start + timedelta(days=6)
            return {"field": field_name, "operator": "date_between", "values": [start, end]}

        if "today" in q_lower:
            field_name = "Created_Time" if ("created" in q_lower or module != "Deals") else "Closing_Date"
            return {"field": field_name, "operator": "date_equals", "values": [current_date]}

        if "yesterday" in q_lower:
            field_name = "Created_Time" if ("created" in q_lower or module != "Deals") else "Closing_Date"
            return {"field": field_name, "operator": "date_equals", "values": [current_date - timedelta(days=1)]}

        # between DATE and DATE
        between_date_match = re.search(r"\b(?:between|created\s+between)\s+([a-zA-Z0-9\s,]+)\s+(?:and|to)\s+([a-zA-Z0-9\s,]+)", q_lower)
        if between_date_match:
            val1 = FilterService.parse_date_value(between_date_match.group(1))
            val2 = FilterService.parse_date_value(between_date_match.group(2))
            # Ensure they are not numeric digits
            if val1 and val2 and not (between_date_match.group(1).strip().isdigit() and between_date_match.group(2).strip().isdigit()):
                # Find if there's an explicit field
                explicit_field = None
                for key in mapping.keys():
                    if key in q_lower.split("between")[0]:
                        explicit_field = mapping[key]
                        break
                field_name = explicit_field or ("Created_Time" if ("created" in q_lower or module != "Deals") else "Closing_Date")
                return {"field": field_name, "operator": "date_between", "values": [min(val1, val2), max(val1, val2)]}

        # after DATE
        after_match = re.search(r"\b(?:after|created\s+after)\s+([a-zA-Z0-9\s,]+)", q_lower)
        if after_match:
            val = FilterService.parse_date_value(after_match.group(1))
            if val:
                explicit_field = None
                for key in mapping.keys():
                    if key in q_lower.split("after")[0]:
                        explicit_field = mapping[key]
                        break
                field_name = explicit_field or ("Created_Time" if ("created" in q_lower or module != "Deals") else "Closing_Date")
                return {"field": field_name, "operator": "date_after", "values": [val]}

        # before DATE
        before_match = re.search(r"\b(?:before|created\s+before)\s+([a-zA-Z0-9\s,]+)", q_lower)
        if before_match:
            val = FilterService.parse_date_value(before_match.group(1))
            if val:
                explicit_field = None
                for key in mapping.keys():
                    if key in q_lower.split("before")[0]:
                        explicit_field = mapping[key]
                        break
                field_name = explicit_field or ("Created_Time" if ("created" in q_lower or module != "Deals") else "Closing_Date")
                return {"field": field_name, "operator": "date_before", "values": [val]}

        # 2. Numeric Range ("between X and Y")
        # Explicit field matching
        between_match = re.search(
            r"\b(" + "|".join(mapping.keys()) + r")\s+(?:is\s+)?between\s+([\d\.\s\w,₹$]+?)\s+(?:and|to)\s+([\d\.\s\w,₹$]+)",
            q_lower
        )
        if between_match:
            field_name = mapping[between_match.group(1)]
            val1 = FilterService.parse_number_value(between_match.group(2))
            val2 = FilterService.parse_number_value(between_match.group(3))
            if val1 is not None and val2 is not None:
                return {"field": field_name, "operator": "between", "values": [min(val1, val2), max(val1, val2)]}
                
        # Implicit/Default field matching
        between_impl = re.search(
            r"\b(?:deals|leads|opportunities|accounts|companies|contacts)?\s*(?:is\s+)?between\s+([\d\.\s\w,₹$]+?)\s+(?:and|to)\s+([\d\.\s\w,₹$]+)",
            q_lower
        )
        if between_impl:
            field_name = DEFAULT_FIELDS.get(module, {}).get("numeric")
            val1 = FilterService.parse_number_value(between_impl.group(1))
            val2 = FilterService.parse_number_value(between_impl.group(2))
            if field_name and val1 is not None and val2 is not None:
                return {"field": field_name, "operator": "between", "values": [min(val1, val2), max(val1, val2)]}

        # 3. Numeric Operators
        # Explicit field matching
        num_match = re.search(
            r"\b(" + "|".join(mapping.keys()) + r")\s+(?:is\s+)?(greater\s+than\s+or\s+equal\s+to|less\s+than\s+or\s+equal\s+to|greater\s+than|less\s+than|equals|is\s+not|not\s+equals|not\s+equal)\s+([\d\.\s\w,₹$]+)",
            q_lower
        )
        if num_match:
            field_name = mapping[num_match.group(1)]
            op_str = num_match.group(2)
            val = FilterService.parse_number_value(num_match.group(3))
            if val is not None:
                op = "gte" if "greater than or equal" in op_str else ("lte" if "less than or equal" in op_str else ("gt" if "greater" in op_str else ("lt" if "less" in op_str else ("not_equals" if ("not" in op_str or "not equal" in op_str) else "equals"))))
                return {"field": field_name, "operator": op, "values": [val]}
                
        # Implicit/Default field matching
        num_impl = re.search(
            r"\b(?:is\s+)?(greater\s+than\s+or\s+equal\s+to|less\s+than\s+or\s+equal\s+to|greater\s+than|less\s+than|equals|is\s+not|not\s+equals|not\s+equal)\s+([\d\.\s\w,₹$]+)",
            q_lower
        )
        if num_impl:
            field_name = DEFAULT_FIELDS.get(module, {}).get("numeric")
            op_str = num_impl.group(1)
            val = FilterService.parse_number_value(num_impl.group(2))
            if field_name and val is not None:
                op = "gte" if "greater than or equal" in op_str else ("lte" if "less than or equal" in op_str else ("gt" if "greater" in op_str else ("lt" if "less" in op_str else ("not_equals" if ("not" in op_str or "not equal" in op_str) else "equals"))))
                return {"field": field_name, "operator": op, "values": [val]}

        # 4. String Operators
        # Explicit field matching
        str_match = re.search(
            r"\b(" + "|".join(mapping.keys()) + r")\s+(starts\s+with|starting\s+with|ends\s+with|ending\s+with|contains|containing|equals|not\s+equals|is\s+not|is)\s+([a-zA-Z0-9_\-\.\@\s'\"]+)",
            q_lower
        )
        if str_match:
            field_name = mapping[str_match.group(1)]
            op_str = str_match.group(2)
            val = str_match.group(3).strip().strip("'\"")
            op = "starts_with" if "start" in op_str else ("ends_with" if "end" in op_str else ("contains" if "contain" in op_str else ("not_equals" if ("not" in op_str) else "equals")))
            return {"field": field_name, "operator": op, "values": [val]}
            
        # Implicit/Default field matching
        str_impl = re.search(
            r"\b(?:starts\s+with|starting\s+with|ends\s+with|ending\s+with|contains|containing|equals|not\s+equals|is\s+not|is)\s+([a-zA-Z0-9_\-\.\@\s'\"]+)",
            q_lower
        )
        if str_impl:
            field_name = QueryUnderstanding.detect_filter_field(q_lower)
            if field_name is None:
                field_name = DEFAULT_FIELDS.get(module, {}).get("string")
            op_str = q_lower
            val = str_impl.group(1).strip().strip("'\"")
            op = "starts_with" if "start" in op_str else ("ends_with" if "end" in op_str else ("contains" if "contain" in op_str else ("not_equals" if ("not" in op_str) else "equals")))
            if field_name:
                return {"field": field_name, "operator": op, "values": [val]}

        return None

    @staticmethod
    def check_filter_ambiguity(query: str, module: str) -> Optional[Dict[str, Any]]:
        """Check if the query is ambiguous for the given module."""
        q_lower = query.lower().strip()
        
        # 1. Leads ambiguity: "Show leads starting with D"
        if module == "Leads":
            m = re.search(r"\bleads\s+(?:starts\s+with|starting\s+with|starts)\s+['\"]?([a-zA-Z0-9])['\"]?\b", q_lower)
            if m:
                val = m.group(1).upper()
                return {
                    "type": "ambiguity",
                    "clarification_key": "leads_starts_with",
                    "value": val,
                    "message": f"Do you mean Lead Name starts with '{val}' or Company Name starts with '{val}'?"
                }
                
        # 2. Accounts ambiguity: "Show accounts starting with T"
        if module == "Accounts":
            m = re.search(r"\b(?:accounts|companies)\s+(?:starts\s+with|starting\s+with|starts)\s+['\"]?([a-zA-Z0-9])['\"]?\b", q_lower)
            if m:
                val = m.group(1).upper()
                return {
                    "type": "ambiguity",
                    "clarification_key": "accounts_starts_with",
                    "value": val,
                    "message": f"Do you mean Account Name starts with '{val}' or Industry starts with '{val}'?"
                }
                
        return None
    
    
    @staticmethod
    def execute_filter(records: list, filter_def: Dict[str, Any]) -> list:
        """Apply the parsed filter definition to a list of records."""
        field = filter_def["field"]
        op = filter_def["operator"]
        vals = filter_def["values"]
        
        filtered = []
        for rec in records:
            val = rec.get(field)
            
            # Fallback for Leads Full_Name
            if field == "Full_Name" and val is None:
                fn = rec.get("First_Name") or ""
                ln = rec.get("Last_Name") or ""
                val = f"{fn} {ln}".strip() or None
                
            if isinstance(val, dict):
                val = val.get("name") or val.get("id") or ""
                
            if val is None:
                continue
                
            # -----------------------------
            # DATE FILTERS
            # -----------------------------
            if op in [
                "after",
                "before",
                "date_after",
                "date_before",
                "date_between",
                "date_equals",
                "equals",
            ]:

                rec_date = FilterService.parse_record_date(val)

                if rec_date is None:
                    continue

                filter_dates = []

                for v in vals:

                    if hasattr(v, "year") and hasattr(v, "month") and hasattr(v, "day"):
                        filter_dates.append(date(v.year, v.month, v.day))

                    else:

                        parsed = FilterService.parse_date_value(str(v))

                        if parsed is None:
                            continue

                        filter_dates.append(parsed)

                if not filter_dates:
                    continue

                if op in ["after", "date_after"]:
                    print( f"Comparing {rec_date} > {filter_dates[0]} = {rec_date > filter_dates[0]}")

                    if rec_date > filter_dates[0]:
                        filtered.append(rec)

                elif op in ["before", "date_before"]:

                    if rec_date < filter_dates[0]:
                        filtered.append(rec)

                elif op == "date_between":

                    if filter_dates[0] <= rec_date <= filter_dates[1]:
                        filtered.append(rec)

                elif op in ["equals", "date_equals"]:

                    if rec_date == filter_dates[0]:
                        filtered.append(rec)

                continue

            val_str = str(val).lower().strip()
            print(field, "=", val)
            if op == "starts_with":
                if val_str.startswith(str(vals[0]).lower()):
                    filtered.append(rec)
            elif op == "ends_with":
                if val_str.endswith(str(vals[0]).lower()):
                    filtered.append(rec)
            elif op == "contains":
                if str(vals[0]).lower() in val_str:
                    filtered.append(rec)
            
            elif op == "equals":

                target = str(vals[0]).lower().strip()

                if field in ["Lead_Status", "Stage", "Status"]:

                    if target in val_str:
                        filtered.append(rec)

                else:

                    if val_str == target:
                        filtered.append(rec)
            elif op == "not_equals":

                target = str(vals[0]).lower().strip()

                if field in ["Lead_Status", "Stage", "Status"]:

                    if target not in val_str:
                        filtered.append(rec)

                else:

                    if val_str != target:
                        filtered.append(rec)
                    
            elif op in [
                "gt",
                "lt",
                "gte",
                "lte",
                "greater_than",
                "less_than",
                "greater_than_or_equal",
                "less_than_or_equal",
                "between"
            ]:
                try:

                    numeric_val = FilterService.parse_number_value(str(val))

                    if numeric_val is None:
                        continue

                    if op in ["gt", "greater_than"]:

                        if numeric_val > vals[0]:
                            filtered.append(rec)

                    elif op in ["lt", "less_than"]:

                        if numeric_val < vals[0]:
                            filtered.append(rec)

                    elif op in ["gte", "greater_than_or_equal"]:

                        if numeric_val >= vals[0]:
                            filtered.append(rec)

                    elif op in ["lte", "less_than_or_equal"]:

                        if numeric_val <= vals[0]:
                            filtered.append(rec)

                    elif op == "between":

                        if vals[0] <= numeric_val <= vals[1]:
                            filtered.append(rec)

                except:

                    pass
                    
        return filtered

    
    @staticmethod
    def apply_filter(records, module, filter_request):
        """
        Apply a structured filter generated by QueryUnderstanding.

        filter_request example:
        {
            "field": "Lead_Status",
            "operator": "equals",
            "values": ["Lost"]
        }
        """

        if not records:
            return []

        if not filter_request:
            return records

        field = filter_request.get("field")
        operator = filter_request.get("operator")
        values = filter_request.get("values", [])

        filter_def = {
            "field": field,
            "operator": operator,
            "values": values,
        }

        return FilterService.execute_filter(records, filter_def)
    
    @staticmethod
    def apply_deterministic_filters(query: str, records: list, module: str) -> Optional[Any]:
        """
        Check if a query has a deterministic filter or ambiguity and apply it.
        Returns filtered list of records, or ambiguity dict, or None.
        """
        normalized = FilterService.normalize_query(query)
        
        # 1. Ambiguity check (on normalized query)
        ambiguity = FilterService.check_filter_ambiguity(normalized, module)
        if ambiguity:
            return ambiguity
            
        # 2. Parse filter
        filter_def = FilterService.parse_filter_query(normalized, module)
        if filter_def:
            log_path = r"C:\Users\golis\.gemini\antigravity\brain\395a2050-730b-4753-b5e2-6ead825caa8d\scratch\filtering_debug.log"
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.now().isoformat()}] --- Deterministic Filter Execution Log ---\n")
                f.write(f"[{datetime.now().isoformat()}] Original Query: {query}\n")
                f.write(f"[{datetime.now().isoformat()}] Normalized Query: {normalized}\n")
                f.write(f"[{datetime.now().isoformat()}] Parsed Operator: {filter_def['operator']}\n")
                f.write(f"[{datetime.now().isoformat()}] Parsed Field: {filter_def['field']}\n")
                f.write(f"[{datetime.now().isoformat()}] Parsed Value: {filter_def['values']}\n")
                f.write(f"[{datetime.now().isoformat()}] Module: {module}\n")
                f.write(f"[{datetime.now().isoformat()}] Raw record count before filtering: {len(records)}\n")
                
            filtered = FilterService.execute_filter(records, filter_def)
            
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] Filtered record count: {len(filtered)}\n")
                f.write(f"[{datetime.now().isoformat()}] --- End Deterministic Filter Log ---\n")
                
            print(f"[Deterministic Filter] Matches! Operator: {filter_def['operator']}, Field: {filter_def['field']}, Value: {filter_def['values']}. Filtered: {len(records)} -> {len(filtered)}", flush=True)
            return filtered
            
        return None