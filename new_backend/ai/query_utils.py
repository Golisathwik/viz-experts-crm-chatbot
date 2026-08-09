import re

class QueryUtils:

    @staticmethod
    def normalize_query(query: str) -> str:

        q = query.lower().strip()

        replacements = {
            "show me": "show",
            "give me": "show",
            "list me": "list",
            "can you": "",
            "could you": "",
            "would you": "",
            "please": "",
            "i need": "",
            "i want": "",
            "i would like": "",
            "tell me": "show",
            "find me": "find",
            "display": "show",
        }

        for old, new in replacements.items():
            q = re.sub(rf"\b{re.escape(old)}\b", new, q)

        q = re.sub(r"\bi am\s+\w+\b", "", q)
        q = re.sub(r"\bmy name is\s+\w+\b", "", q)

        if q in {"show", "list", "find"}:
            return ""

        return q