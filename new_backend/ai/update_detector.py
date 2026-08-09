import re
from typing import Optional


class UpdateDetector:

    @staticmethod
    def extract_update_details_deterministic(query: str) -> Optional[dict]:
        p = query.strip()
        if p.endswith("."):
            p = p[:-1].strip()

        fields_pattern = (
            r"(annual revenue|revenue|amount|deal value|value|"
            r"email address|email id|mail address|mail id|mail|email|"
            r"phone number|phone|mobile number|mobile|cell number|cell|"
            r"status|lead status|deal stage|stage|closing date|closing_date|"
            r"website url|website|url|"
            r"number of employees|number of employee|no of employees|no\. of employees|employee count|employees|employee|"
            r"company name|company|assistant|department|title|probability)"
        )
        # Commands that do not specify a record
        field_only_pattern = re.match(
            r"^(?:update|set|change|edit|modify)\s+(?:the\s+)?"
            + fields_pattern +
            r"\s+(?:to|as|=)\s+(.+)$",
            p,
            re.IGNORECASE,
        )

        if field_only_pattern:
            field_name, new_value = field_only_pattern.groups()

            return {
                "target_record": None,
                "field_name": field_name.lower().strip(),
                "new_value": new_value.strip(),
            }

        # change goli annual revenue to 100000
        pattern1 = (
            r"^(?:update|set|change|edit|modify)\s+"
            r"(?:lead|contact|account|deal|opportunity\s+)?"
            r"(.+?)\s+"
            r"(annual revenue|lead status|deal stage|closing date|company name|"
            r"phone number|mobile number|number of employees|number of employee|no of employees|no\. of employees|employee count|employees|employee|"
            r"email|phone|mobile|status|stage|amount|deal value|value|"
            r"website|url|revenue|employees|company|assistant|department|title|probability)"
            r"\s+(?:to|as|=)\s+(.+)$"
        )

        m = re.match(pattern1, p, re.IGNORECASE)
        if m:
            target_record, field_name, new_value = m.groups()

            target_record = target_record.strip()
            field_name = UpdateDetector.normalize_field_name(field_name)
            new_value = new_value.strip()

            candidate = re.sub(
                r"^(the|this)\s+",
                "",
                target_record,
                flags=re.IGNORECASE,
            ).strip()

            # If the "record" is only a field phrase,
            # then no record was actually specified.

            field_aliases = {
                field_name,
                "employee",
                "employees",
                "number of employee",
                "number of employees",
                "employee count",
                "phone",
                "phone number",
                "mobile",
                "mobile number",
                "cell",
                "cell number",
                "email",
                "email id",
                "email address",
                "mail",
                "mail id",
                "mail address",
                "website",
                "url",
                "company",
                "company name",
                "annual revenue",
                "revenue",
                "lead status",
                "status",
                "deal stage",
                "stage",
                "amount",
                "value",
            }

            if candidate.lower() in field_aliases:
                candidate = None

            elif candidate.lower().endswith(field_name):
                remaining = candidate[:-len(field_name)].strip()
                candidate = remaining if remaining else None

            return {
                "target_record": candidate,
                "field_name": field_name,
                "new_value": new_value,
            }

        # change annual revenue for goli to 100000
        pattern2 = (
            r"^(?:update|set|change|edit|modify)\s+"
            + fields_pattern +
            r"\s+(?:for|of|on)\s+(.+?)\s+(?:to|as|=)\s+(.+)$"
        )

        m = re.match(pattern2, p, re.IGNORECASE)
        if m:
            field_name, target_record, new_value = m.groups()

            return {
                "target_record": target_record.strip(),
                "field_name": field_name.lower().strip(),
                "new_value": new_value.strip()
            }
            

        # change annual revenue to 100000
        pattern3 = (
            r"^(?:update|set|change|edit|modify)\s+"
            r"(?:(?:the|a|an)\s+)?"
            + fields_pattern +
            r"\s+(?:to|as|=)\s+(.+)$"
        )

        m = re.match(pattern3, p, re.IGNORECASE)
        if m:
            field_name, new_value = m.groups()

            return {
                "target_record": None,
                "field_name": field_name.lower().strip(),
                "new_value": new_value.strip()
            }

        # ---------------------------------------------------------
        # Partial update request
        # Examples:
        # update phone
        # change email
        # edit website
        # modify lead status
        # ---------------------------------------------------------

        pattern4 = (
            r"^(?:update|set|change|edit|modify)\s+"
            r"(?:(?:the|a|an)\s+)?"
            + fields_pattern +
            r"$"
        )

        m = re.match(pattern4, p, re.IGNORECASE)

        if m:
            field_name = m.group(1)

            return {
                "target_record": None,
                "field_name": field_name.lower().strip(),
                "new_value": None,
            }
            
    @staticmethod
    def normalize_field_name(field_name: str) -> str:
        mapping = {
            "email id": "email",
            "email address": "email",
            "mail": "email",
            "mail id": "email",
            "mail address": "email",

            "phone number": "phone",
            "mobile": "phone",
            "mobile number": "phone",
            "cell": "phone",
            "cell number": "phone",

            "website url": "website",
            "company name": "company",
        }

        field = field_name.lower().strip()
        return mapping.get(field, field)

    @staticmethod
    def is_update_request(query: str) -> bool:

        q = query.lower().strip()

        return q.startswith(("update", "set", "change"))