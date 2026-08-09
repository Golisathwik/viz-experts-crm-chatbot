import re
from typing import Any, Dict, Optional
from new_backend.ai.module_detector import ModuleDetector
from new_backend.ai.query_utils import QueryUtils

class SearchDetector:

    @staticmethod
    def detect_requested_fields(query: str) -> list[str]:
        field_mappings = {
            "Phone": [r"\bphone\b", r"\bmobile\b", r"\bcell\b"],
            "Email": [r"\bemail\b"],
            "Contact": [r"\bcontact\b"],
            "Owner": [r"\bowner\b", r"\bowned\b", r"\bassigned\b"],
            "Annual_Revenue": [r"\brevenue\b", r"\bannual\s+revenue\b", r"\bturnover\b"],
            "Website": [r"\bwebsite\b", r"\burl\b"],
            "Address": [r"\baddress\b", r"\bstreet\b", r"\bcity\b", r"\bstate\b", r"\bcountry\b", r"\bzip\b"],
            "Company": [r"\bcompany\b"],
            "Industry": [r"\bindustry\b"],
            "Rating": [r"\brating\b"],
            "No_of_Employees": [r"\bemployee\b", r"\bemployees\b"],
            "Stage": [r"\bstage\b"],
            "Amount": [r"\bamount\b", r"\bdeal\s+value\b"],
            "Lead_Status": [r"\bstatus\b", r"\blead\s+status\b"]
        }
        target_fields = []
        p_clean = query.strip().lower()
        p_clean = re.sub(r"[?!.]", "", p_clean).strip()
        
        # Check if the query matches a field pattern and is short
        if len(p_clean.split()) <= 12:
            for field, patterns in field_mappings.items():
                for pat in patterns:
                    if re.search(pat, p_clean):
                        target_fields.append(field)
                        break
        return target_fields

    @staticmethod
    def extract_search_request(query: str) -> Optional[Dict[str, Any]]:

        q_original = query.strip()
        q = QueryUtils.normalize_query(q_original)
        
        if not q:
            return None

        module = ModuleDetector.detect_module(q)
        if module is None:
            module = "All"

        requested_fields = SearchDetector.detect_requested_fields(q)
        # If the query is asking for complete/full details,
        # don't interpret field names inside the record name.
        detail_words = [
            "details",
            "detail",
            "complete",
            "full",
            "information",
            "info",
            "profile",
        ]

        if any(word in q.lower() for word in detail_words):
            requested_fields = []

        # Search prefix is optional.
        # If the query starts with a search verb we remove it.
        # Otherwise we still allow natural-language entity searches.

        if re.match(
            r"^(find|search|lookup|who is|show|display|get|list)\b",
            q,
            flags=re.IGNORECASE,
        ):
            q = re.sub(
                r"^(find|search|lookup|who is|show|display|get|list)\b",
                "",
                q,
                flags=re.IGNORECASE,
            ).strip()

        q = re.sub(
            r"\b(show|find|search|get|display|list|tell me about|who is|lookup)\b",
            " ",
            q,
            flags=re.IGNORECASE,
        )

        q = re.sub(
            r"\b(details?|detail|information|info|profile|record|records|complete|completely|full|entire)\b",
            " ",
            q,
            flags=re.IGNORECASE,
        )

        q = re.sub(
            r"\b(lead|leads|contact|contacts|account|accounts|company|companies|deal|deals|opportunity|opportunities)\b",
            " ",
            q,
            flags=re.IGNORECASE,
        )

        q = re.sub(
            r"\b(of|for|from|named|called|with|whose|the|me|and|give|show|tell|please)\b",
            " ",
            q,
            flags=re.IGNORECASE,
        )

        q = re.sub(r"\s+", " ", q).strip()
        # Don't treat "all" or "everything" as a search term
        if q.lower() in {
            "",
            "all",
            "everything",
            "all records",
            "all data",
            "chart",
            "graph",
            "dashboard",
            "analytics",
            "visualization",
            "summary",
            "breakdown",
            "distribution",
        }:
            return None

        if not q:
            return None
        
        ignore_terms = {
            "chart",
            "graph",
            "dashboard",
            "analytics",
            "visualization",
            "summary",
            "breakdown",
            "distribution",
            "status chart",
            "lead status",
            "lead status chart",
        }

        if q.lower().strip() in ignore_terms:
            return None
        # If something meaningful remains, treat it as a search term.
        if len(q.split()) >= 1:
            return {
                "module": module,
                "search_term": q,
                "value": q,
                "requested_fields": requested_fields,
                "details": bool(requested_fields),
            }
        

        return {
            "module": module,
            "search_term": q,
            "value": q,                 # Backward compatibility
            "requested_fields": requested_fields,
            "details": bool(requested_fields),
        }
    @staticmethod
    def detect_search(query: str) -> Optional[Dict[str, Any]]:
        q = QueryUtils.normalize_query(query)
        search_request = SearchDetector.extract_search_request(query)

        if search_request:
            search_request.setdefault(
                "value",
                search_request["search_term"]
            )
            return search_request
        
        
        if not q:
            return None
        q_lower = q

        # Ignore sorting queries
        if "sort" in q_lower or "sorted" in q_lower:
            return None

        # Ignore filter queries
        filter_words = [
            "greater", "less", "between", "after", "before",
            "contains", "starting", "starts", "ending",
            "equals", "only"
        ]

        if any(word in q_lower for word in filter_words):
            return None

        # Common search prefixes
        prefixes = [
            "show lead",
            "show leads",
            "show contact",
            "show contacts",
            "show account",
            "show accounts",
            "show deal",
            "show deals",
            "find",
            "search",
            "search for",
            "find me"
        ]

        for prefix in prefixes:
            if q_lower.startswith(prefix):
                term = q[len(prefix):].strip()

                if not term or len(term) <= 1:
                    return None

                return {
                    "search_term": term
                }
        return None

    @staticmethod
    def extract_clean_search_term(query: str) -> str:
        q = query.strip()
        q = re.sub(r"[?.,!:]", "", q)
        q_lower = q.lower()
        
        prefixes = [
            "who is the owner of", "find contact for", "find lead for", "show details of", 
            "tell me about", "get details for", "get details of", "i need details for", 
            "i need details of", "search for", "find contact", "find lead", "details of", 
            "details for", "show me", "who is", "search", "find", "show", "get", "i need",
            "give me complete details of", "give me details of", "give me details for",
            "give me complete details for", "complete details of", "complete details for",
            "named", "called", "by name"
        ]
        
        prefixes.sort(key=lambda x: -len(x))
        
        for prefix in prefixes:
            if q_lower.startswith(prefix + " "):
                q = q[len(prefix) + 1:].strip()
                q_lower = q.lower()
                break
                
        module_nouns = ["lead", "contact", "account", "deal", "leads", "contacts", "accounts", "deals"]
        for noun in module_nouns:
            if q_lower.startswith(noun + " "):
                q = q[len(noun) + 1:].strip()
                q_lower = q.lower()
                break
                
        words = q.split()
        stop_words = {
            "named", "called", "lead", "leads", "contact", "contacts", "account", "accounts",
            "deal", "deals", "details", "complete", "info", "information", "of", "for", "the", "a", "an", "named:",
            "about", "me", "show", "find", "search", "get"
        }
        
        filtered_words = [w for w in words if w.lower() not in stop_words]
        
        if filtered_words:
            cleaned_words = [re.sub(r"\W+", "", w) for w in filtered_words]
            cleaned_words = [w for w in cleaned_words if len(w) >= 2]
            if cleaned_words:
                return " ".join(cleaned_words)
        
        return q

    @staticmethod
    def has_search_keyword(query: str):

        q = query.lower().strip()

        return any(
            q.startswith(k)
            for k in [
                "find",
                "search",
                "lookup",
                "show",
                "get",
            ]
        )