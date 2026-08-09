import json

from new_backend.ai.llm.router import get_ai_router


class CreateFieldExtractor:

    @staticmethod
    async def extract_fields(
        module: str,
        user_text: str,
        api_keys: dict,
    ):

        router = get_ai_router()

        system_prompt = f"""
You are a Zoho CRM data extraction engine.

Your job is to extract CRM fields from natural language.

Module:
{module}

Rules:

1. Return ONLY JSON.

2. Do not explain anything.

3. Do not use markdown.

4. If a field is missing, omit it.

5. Preserve original values.

6. If a value is unknown, do not guess.

Lead Fields:

First_Name
Last_Name
Company
Email
Phone
Mobile
Lead_Source
Lead_Status
Industry
Annual_Revenue
Website
City
State
Country
Description

Contact Fields:

First_Name
Last_Name
Email
Phone
Mobile
Mailing_City
Mailing_State
Mailing_Country
Description

Account Fields:

Account_Name
Website
Phone
Industry
Annual_Revenue
City
State
Country
Description

Deal Fields:

Deal_Name
Stage
Amount
Closing_Date
Description
Extraction Rules

Employees examples

Input:
14 employees

Output:
Employees = 14

Input:
There are 24 employees

Output:
Employees = 24

Input:
Our company has 300 employees

Output:
Employees = 300

Never map these to:
Account_Name
Company
Description

Annual Revenue must always be numeric.

Employees must always be numeric.

Phone must always contain only phone numbers.

Email must always contain an email address.

Website must always contain a valid website.

If the user is only answering the last requested field, return ONLY that field.

Never replace previously extracted values with null.

Return ONLY JSON.
"""

        result = await router.extract_json(
            prompt=user_text,
            system_prompt=system_prompt,
            api_keys=api_keys,
        )

        if not isinstance(result, dict):
            return {}

        # -----------------------------
        # Auto split names
        # -----------------------------

        # Case 1:
        # Name : "John Smith"

        if "Name" in result:

            parts = str(result.pop("Name")).strip().split()

            if len(parts) == 1:
                result["Last_Name"] = parts[0]

            elif len(parts) >= 2:
                result["First_Name"] = parts[0]
                result["Last_Name"] = " ".join(parts[1:])


        # Case 2:
        # Only First_Name extracted but contains two words

        if "First_Name" in result:

            value = str(result["First_Name"]).strip()

            if " " in value:

                parts = value.split()

                result["First_Name"] = parts[0]
                result["Last_Name"] = " ".join(parts[1:])


        # Case 3:
        # Only Last_Name extracted but contains two words

        if "Last_Name" in result:

            value = str(result["Last_Name"]).strip()

            if " " in value:

                parts = value.split()

                result["First_Name"] = parts[0]
                result["Last_Name"] = " ".join(parts[1:])


        return result