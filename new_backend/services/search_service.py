import re
from typing import Optional, List, Tuple, Any
from new_backend.repositories.chat_session_repository import ChatSessionRepository
from new_backend.crm.zoho_client import ZohoCRMClient

class SearchService:
    @staticmethod
    def determine_entity_type_and_search_order(query_term: str, user_query: Optional[str] = None) -> List[str]:
        term = query_term.strip().lower()
        if "@" in term and re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", term):
            return ["Contacts", "Leads"]
        cleaned_phone = re.sub(r"[\s\-\+\(\)]", "", term)
        if cleaned_phone.isdigit() and len(cleaned_phone) >= 7:
            return ["Leads", "Contacts", "Accounts"]
        context_text = (user_query or "").lower() + " " + term
        deal_keywords = ["deal", "deals", "opportunity", "opportunities", "pipeline", "stage"]
        if any(k in context_text for k in deal_keywords):
            return ["Deals", "Accounts"]
        return ["Leads", "Contacts", "Accounts", "Deals"]

    # Prioritized Targeted Search
    @staticmethod
    def generate_progressive_queries(query: str) -> List[str]:
        q = query.strip()
        if not q:
            return []
        queries = [q]
        
        # Relax suffix words progressively
        words = q.split()
        while len(words) > 1:
            last_word_lower = words[-1].lower().replace(".", "").replace(",", "")
            generic_words = {"company", "industry", "corp", "corporation", "ltd", "limited", "inc", "incorporated", "co"}
            if last_word_lower in generic_words:
                words.pop()
                candidate = " ".join(words)
                if candidate not in queries:
                    queries.append(candidate)
            else:
                break
                
        # Also fallback to first word if >= 3 characters
        if len(words) > 1:
            first_word = words[0]
            if len(first_word) >= 3 and first_word not in queries:
                queries.append(first_word)
                
        return queries

    @staticmethod
    def perform_prioritized_search(client: ZohoCRMClient, query: str, detected_module: Optional[str] = None, user_query: Optional[str] = None, session_id: Optional[int] = None) -> List[Tuple[str, dict]]:
        if not query or not query.strip():
            return []
        
        # Fetch active context to bypass Zoho search index latency for recently updated record
        active_id = None
        active_mod = None
        if session_id:
            try:
                active_ctx = ChatSessionRepository.get_chat_session_active_context(session_id)
                active_id = active_ctx.get("active_record_id")
                active_mod = active_ctx.get("active_module")
            except Exception:
                pass

        if detected_module:
            search_order = [detected_module]
        else:
            search_order = SearchService.determine_entity_type_and_search_order(query, user_query)
            
        candidate_queries = SearchService.generate_progressive_queries(query)
        results = []
        
        for module in search_order:
            for q_candidate in candidate_queries:
                try:
                    if module == "Leads":
                        records = client.get_leads(query=q_candidate)
                    elif module == "Contacts":
                        records = client.get_contacts(query=q_candidate)
                    elif module == "Accounts":
                        records = client.get_accounts(query=q_candidate)
                    elif module == "Deals":
                        records = client.get_deals(query=q_candidate)
                    else:
                        records = []
                        
                    if records:
                        final_records = []
                        for r in records:
                            r_id = r.get("id")
                            if r_id and str(r_id) == str(active_id) and module == active_mod:
                                try:
                                    # Fetch fresh record directly by ID to bypass search index latency
                                    fresh_r = client.get_record_by_id(module, r_id)
                                    if fresh_r:
                                        final_records.append(fresh_r)
                                        continue
                                except Exception as e:
                                    print(f"[Latency Bypass Warning] Failed to fetch fresh record {r_id}: {e}")
                            final_records.append(r)
                        results.extend([(module, r) for r in final_records])
                        break
                except Exception as e:
                    print(f"[Search Fallback Warning] Failed to query module {module} with '{q_candidate}': {str(e)}")
                
        return results

    # Name Extractor Helpers
    @staticmethod
    def get_record_display_name(module: str, record: dict) -> str:
        if module in ["Leads", "Contacts"]:
            first = record.get("First_Name") or ""
            last = record.get("Last_Name") or ""
            name = f"{first} {last}".strip()
            return name if name else record.get("id", "Unknown Record")
        elif module == "Accounts":
            return record.get("Account_Name") or record.get("id", "Unknown Account")
        elif module == "Deals":
            return record.get("Deal_Name") or record.get("id", "Unknown Deal")
        return record.get("id", "Unknown")

    @staticmethod
    def get_record_disambiguation_label(module: str, record: dict) -> str:
        name = SearchService.get_record_display_name(module, record)
        module_singular = module[:-1] if module.endswith('s') else module
        details = []
        if module == "Leads":
            company = record.get("Company")
            email = record.get("Email")
            if company:
                details.append(company)
            if email:
                details.append(email)
        elif module == "Contacts":
            account = record.get("Account_Name")
            if isinstance(account, dict):
                account = account.get("name")
            email = record.get("Email")
            if account:
                details.append(account)
            if email:
                details.append(email)
        elif module == "Accounts":
            website = record.get("Website")
            phone = record.get("Phone")
            if website:
                details.append(website)
            if phone:
                details.append(phone)
        elif module == "Deals":
            account = record.get("Account_Name")
            if isinstance(account, dict):
                account = account.get("name")
            stage = record.get("Stage")
            amount = record.get("Amount")
            if account:
                details.append(account)
            if stage:
                details.append(stage)
            if amount is not None:
                details.append(f"${amount}")
                
        details_str = " – ".join(details)
        if details_str:
            return f"{name} ({details_str}) [{module_singular}]"
        return f"{name} [{module_singular}]"
    
    
    @staticmethod
    def build_search_response(records, module):

        if not records:
            return "No matching records were found."

        if len(records) == 1:

            record = records[0]

            name = (
                record.get("Full_Name")
                or record.get("Account_Name")
                or record.get("Deal_Name")
                or record.get("Company")
                or "Record"
            )

            lines = [
                f"Found 1 record in {module}.",
                "",
                f"Name: {name}",
            ]

            important_fields = [
                "Company",
                "Email",
                "Phone",
                "Industry",
                "Lead_Status",
                "Account_Name",
                "Website",
                "Annual_Revenue",
            ]

            for field in important_fields:

                value = record.get(field)

                if value not in (None, "", False):
                    lines.append(f"{field}: {value}")

            return "\n".join(lines)

        return f"Found {len(records)} records in {module}."
    
    
    @staticmethod
    def build_show_response(records, module):

        if not records:
            return f"No {module.lower()} found."

        lines = [
            f"Found {len(records)} {module.lower()}.",
            ""
        ]

        important_fields = {
            "Leads": [
                "Full_Name",
                "Company",
                "Email",
                "Phone",
                "Lead_Status",
                "Industry",
            ],
            "Contacts": [
                "Full_Name",
                "Account_Name",
                "Email",
                "Phone",
            ],
            "Accounts": [
                "Account_Name",
                "Industry",
                "Phone",
                "Website",
                "Annual_Revenue",
            ],
            "Deals": [
                "Deal_Name",
                "Stage",
                "Amount",
                "Closing_Date",
            ],
        }

        fields = important_fields.get(module, [])

        for i, record in enumerate(records, 1):

            lines.append(f"{i}.")

            for field in fields:

                value = record.get(field)

                if value not in (None, "", False):
                    lines.append(f"{field}: {value}")

            lines.append("")

        return "\n".join(lines)