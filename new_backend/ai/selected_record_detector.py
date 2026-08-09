import re


class SelectedRecordDetector:

    FIELD_MAP = {

        # Email
        "email": "Email",
        "mail": "Email",
        "gmail": "Email",
        "email id": "Email",

        # Phone
        "phone": "Phone",
        "phone number": "Phone",
        "mobile": "Mobile",
        "mobile number": "Mobile",
        "contact number": "Phone",

        # Company
        "company": "Company",
        "organization": "Company",
        "organisation": "Company",

        # Status
        "status": "Lead_Status",
        "lead status": "Lead_Status",
        "deal status": "Stage",
        "stage": "Stage",

        # Owner
        "owner": "Owner",
        "assigned to": "Owner",

        # Website
        "website": "Website",
        "site": "Website",

        # Industry
        "industry": "Industry",

        # Revenue
        "revenue": "Annual_Revenue",
        "annual revenue": "Annual_Revenue",
        "income": "Annual_Revenue",

        # Deal Amount
        "amount": "Amount",
        "deal amount": "Amount",
        "price": "Amount",
        "value": "Amount",

        # Lead Source
        "source": "Lead_Source",

        # Address
        "address": "Address",
        "location": "Address",
    }

    @staticmethod
    def detect(query):

        q = query.lower().strip()

        # Remove punctuation
        q = (
            q.replace("?", "")
            .replace(".", "")
            .replace(",", "")
        )

        # Common filler words
        remove_words = [
            "show",
            "display",
            "tell me",
            "give me",
            "what is",
            "what's",
            "can you",
            "please",
            "the",
            "this",
            "that",
            "his",
            "her",
            "its",
            "their",
            "of",
            "for",
            "about",
            "record",
            "lead",
            "deal",
            "contact",
            "account",
        ]

        for word in remove_words:
            q = q.replace(word, " ")

        q = " ".join(q.split())

        # Direct field lookup
        for keyword, field in SelectedRecordDetector.FIELD_MAP.items():

            # Match only if the ENTIRE remaining query is the field request
            if q == keyword:

                return {
                    "field": field
                }

            # Also support:
            # phone details
            # email details
            # website info
            if q in (
                f"{keyword} detail",
                f"{keyword} details",
                f"{keyword} info",
                f"{keyword} information",
            ):
                return {
                    "field": field
                }

        return None