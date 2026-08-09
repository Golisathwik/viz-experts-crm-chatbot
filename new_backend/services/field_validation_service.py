import re
from typing import Optional

READ_ONLY_FIELDS = {
    "id",
    "created_time",
    "modified_time",
    "owner",
    "created_by",
    "modified_by",
    "last_activity_time",
    "exchange_rate",
    "modified_by.name",
    "created_by.name",
    "created_by.id",
    "modified_by.id",
}
LEAD_STATUS_OPTIONS = [
    "Attempted to Contact",
    "Contact in Future",
    "Contacted",
    "Junk Lead",
    "Lost Lead",
    "Not Contacted",
    "Pre Qualified"
]

DEAL_STAGE_OPTIONS = [
    "Qualification",
    "Needs Analysis",
    "Value Proposition",
    "Identify Decision Makers",
    "Proposal/Price Quote",
    "Negotiation/Review",
    "Closed Won",
    "Closed Lost",
    "Closed Lost to Competition"
]


class FieldValidationService:
    
    @staticmethod
    def validate_email(email: str) -> bool:
        email_clean = email.strip()
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return bool(re.match(pattern, email_clean))

    @staticmethod
    def validate_phone(phone: str) -> bool:
        cleaned = re.sub(r"[\s\-\+\(\)]", "", phone.strip())
        return cleaned.isdigit() and len(cleaned) >= 7

    @staticmethod
    def validate_website(url: str) -> bool:
        url_clean = url.strip().lower()
        if not url_clean or " " in url_clean:
            return False
        web_pattern = r"^(https?:\/\/)?(www\.)?[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(\/\S*)?$"
        return bool(re.match(web_pattern, url_clean))

    @staticmethod
    def validate_numeric(val: str) -> bool:
        v = val.strip()
        if not v:
            return False
        cleaned = re.sub(r"[\$,₹\s,]", "", v)
        multiplier = 1.0
        if cleaned.lower().endswith("k"):
            multiplier = 1000.0
            cleaned = cleaned[:-1]
        elif cleaned.lower().endswith("m"):
            multiplier = 1000000.0
            cleaned = cleaned[:-1]
        try:
            float(cleaned)
            return True
        except ValueError:
            return False
        
    @staticmethod
    def parse_numeric_value(val: str) -> float:
        v = val.strip()
        cleaned = re.sub(r"[\$,₹\s,]", "", v)
        multiplier = 1.0
        if cleaned.lower().endswith("k"):
            multiplier = 1000.0
            cleaned = cleaned[:-1]
        elif cleaned.lower().endswith("m"):
            multiplier = 1000000.0
            cleaned = cleaned[:-1]
        return float(cleaned) * multiplier

    @staticmethod
    def validate_and_normalize_option(val: str, field_name: str) -> Optional[str]:
        v = val.strip().lower()
        if field_name == "Lead_Status":
            for opt in LEAD_STATUS_OPTIONS:
                if opt.lower() == v:
                    return opt
        elif field_name == "Stage":
            for opt in DEAL_STAGE_OPTIONS:
                if opt.lower() == v:
                    return opt
        return None
    
    #moved from create_service.py
    @staticmethod
    def validate_field_value(field, value):

        if value is None:
            return True, None, None

        value = str(value).strip()

        if field in ["Phone", "Mobile"]:

            if not re.fullmatch(r"\+?\d{7,15}", value):
                return False, "Please enter a valid phone number.", None

            return True, None, value

        elif field == "Email":

            if not re.fullmatch(r"[^@]+@[^@]+\.[^@]+", value):
                return False, "Please enter a valid email address.", None

            return True, None, value.lower()

        elif field == "Website":

            if "." not in value:
                return False, "Please enter a valid website.", None

            return True, None, value

        elif field in [
            "Annual_Revenue",
            "Employees",
            "Amount",
        ]:

            try:
                normalized = float(str(value).replace(",", ""))
                return True, None, normalized
            except Exception:
                return False, f"{field.replace('_',' ')} must be numeric.", None

        return True, None, value
    
    @staticmethod
    def is_read_only(field_name: str) -> bool:

        return field_name.lower() in READ_ONLY_FIELDS
    
    
    @staticmethod
    def verify_values_match(val_a, val_b):

        if val_a is None or val_b is None:
            return val_a == val_b

        str_a = str(val_a).strip().lower()
        str_b = str(val_b).strip().lower()

        if str_a == str_b:
            return True

        try:
            if float(str_a) == float(str_b):
                return True
        except Exception:
            pass

        return False
    

    @staticmethod
    def get_available_options(field_name):

        if field_name == "Lead_Status":
            return LEAD_STATUS_OPTIONS

        if field_name == "Stage":
            return DEAL_STAGE_OPTIONS

        return None
    
    @staticmethod
    def get_required_fields(module: str):

        return {
            "Leads": [
                "Last_Name",
                "Company",
            ],

            "Contacts": [
                "Last_Name",
            ],

            "Accounts": [
                "Account_Name",
            ],

            "Deals": [
                "Deal_Name",
                "Stage",
            ],

        }.get(module, [])    
        
    @staticmethod
    def get_optional_fields(module: str):

        OPTIONAL_FIELDS = {

            "Leads": [
                "First_Name",
                "Email",
                "Phone",
                "Mobile",
                "Website",
                "Lead_Source",
                "Lead_Status",
                "Industry",
                "Annual_Revenue",
                "City",
                "State",
                "Country",
                "Description",
            ],

            "Contacts": [
                "First_Name",
                "Email",
                "Phone",
                "Mobile",
                "Department",
                "Assistant",
                "Mailing_City",
                "Mailing_State",
                "Mailing_Country",
                "Description",
            ],

            "Accounts": [
                "Website",
                "Phone",
                "Industry",
                "Employees",
                "Annual_Revenue",
                "City",
                "State",
                "Country",
                "Description",
            ],

            "Deals": [
                "Closing_Date",
                "Amount",
                "Probability",
                "Type",
                "Lead_Source",
                "Description",
            ],
        }

        return OPTIONAL_FIELDS.get(module, [])
    
    @staticmethod
    def get_field_labels():

        return {
            "First_Name": "First Name",
            "Last_Name": "Last Name",
            "Company": "Company",
            "Email": "Email",
            "Phone": "Phone",
            "Mobile": "Mobile",
            "Website": "Website",
            "Lead_Source": "Lead Source",
            "Lead_Status": "Lead Status",
            "Industry": "Industry",
            "Annual_Revenue": "Annual Revenue",
            "City": "City",
            "State": "State",
            "Country": "Country",
            "Description": "Description",
            "Department": "Department",
            "Assistant": "Assistant",
            "Mailing_City": "Mailing City",
            "Mailing_State": "Mailing State",
            "Mailing_Country": "Mailing Country",
            "Employees": "Employees",
            "No_of_Employees": "Employees",
            "Account_Name": "Account Name",
            "Deal_Name": "Deal Name",
            "Stage": "Stage",
            "Closing_Date": "Closing Date",
            "Amount": "Amount",
            "Probability": "Probability",
            "Type": "Type",
        }
    
    @staticmethod
    def get_field_mappings():

        return {

            "Leads": {
                "phone": "Phone",
                "phone number": "Phone",
                "mobile": "Phone",
                "cell": "Phone",
                "mobile number": "Phone",

                "email": "Email",
                "email address": "Email",
                "email id": "Email",
                "mail": "Email",
                "mail id": "Email",
                "gmail": "Email",

                "status": "Lead_Status",
                "lead status": "Lead_Status",

                "company": "Company",
                "company name": "Company",

                "website": "Website",
                "url": "Website",
                "website url": "Website",
                "website link": "Website",

                "revenue": "Annual_Revenue",
                "annual revenue": "Annual_Revenue",

                "employee": "No_of_Employees",
                "employees": "No_of_Employees",
                "employee count": "No_of_Employees",

                "first name": "First_Name",
                "last name": "Last_Name",
                "name": "Last_Name",
                "full name": "Full_Name",
            },

            "Contacts": {

                "phone": "Phone",
                "phone number": "Phone",

                "mobile": "Phone",

                "email": "Email",
                "email address": "Email",
                "email id": "Email",
                "mail": "Email",
                "mail id": "Email",
                "gmail": "Email",

                "first name": "First_Name",
                "last name": "Last_Name",
                "name": "Last_Name",

                "assistant": "Assistant",
                "department": "Department",
                "title": "Title",
            },

            "Accounts": {

                "phone": "Phone",

                "website": "Website",

                "name": "Account_Name",
                "account name": "Account_Name",

                "company": "Account_Name",

                "revenue": "Annual_Revenue",

                "employee": "Employees",
                "employees": "Employees",
            },

            "Deals": {

                "stage": "Stage",

                "status": "Stage",

                "amount": "Amount",

                "value": "Amount",

                "price": "Amount",

                "closing date": "Closing_Date",

                "date": "Closing_Date",

                "probability": "Probability",

            }

        }
        
    @staticmethod
    def resolve_field_name(
        module: str,
        raw_field: str,
        record: dict = None,
    ):
        """
        Resolve user field name to actual Zoho CRM field.
        """

        if not raw_field:
            return None

        module_mappings = FieldValidationService.get_field_mappings().get(
            module,
            {},
        )

        clean = raw_field.strip().lower()

        resolved = module_mappings.get(clean)

        if resolved:
            return resolved

        for _, value in module_mappings.items():

            if value.lower() == clean:
                return value

        if record:

            target = clean.replace(" ", "_")

            for key in record.keys():

                k = key.lower()

                if (
                    k == target
                    or
                    k.replace("_", "") == target.replace("_", "")
                ):
                    return key

        return None
    
    @staticmethod
    def validate_required_fields(
        module: str,
        extracted_fields: dict,
    ):
        """
        Returns:
        {
            "complete": bool,
            "missing": [...]
        }
        """

        required = FieldValidationService.get_required_fields(module)

        missing = []

        for field in required:

            value = extracted_fields.get(field)

            if value in [None, "", []]:
                missing.append(field)

        return {
            "complete": len(missing) == 0,
            "missing": missing,
        }
        
    @staticmethod
    def get_remaining_optional_fields(
        module: str,
        collected_fields: dict,
    ):

        remaining = []

        for field in FieldValidationService.get_optional_fields(module):

            value = collected_fields.get(field)

            if value in [None, "", []]:
                remaining.append(field)
                
        print("\n========== OPTIONAL DEBUG ==========")
        print("MODULE:", module)
        print("COLLECTED:", collected_fields)
        print("REMAINING:", remaining)
        print("===================================\n")

        return remaining
    
    @staticmethod
    def get_display_order(module: str):

        return {

            "Leads": [
                "First_Name",
                "Last_Name",
                "Company",
                "Email",
                "Phone",
                "Mobile",
                "Website",
                "Lead_Source",
                "Lead_Status",
                "Industry",
                "Annual_Revenue",
                "City",
                "State",
                "Country",
                "Description",
            ],

            "Contacts": [
                "First_Name",
                "Last_Name",
                "Email",
                "Phone",
                "Mobile",
                "Department",
                "Assistant",
                "Mailing_City",
                "Mailing_State",
                "Mailing_Country",
                "Description",
            ],

            "Accounts": [
                "Account_Name",
                "Phone",
                "Website",
                "Industry",
                "Employees",
                "Annual_Revenue",
                "City",
                "State",
                "Country",
                "Description",
            ],

            "Deals": [
                "Deal_Name",
                "Stage",
                "Closing_Date",
                "Amount",
                "Probability",
                "Type",
                "Lead_Source",
                "Description",
            ],

        }.get(module, [])