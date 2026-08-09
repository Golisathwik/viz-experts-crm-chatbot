import json
from typing import Optional
from new_backend.repositories.action_repository import ActionRepository
from new_backend.repositories.chat_session_repository import ChatSessionRepository
from new_backend.crm.zoho_client import ZohoCRMClient
from new_backend.services.search_service import SearchService
from new_backend.services.cache_service import CacheService

class DeleteService:
    
    @staticmethod
    def build_response(message: str, module=None):
        return {
            "operation": "delete",
            "module": module,
            "response": message,
            "records": [],
            "table": None,
            "chart": None,
            "kpis": None,
            "summary": None,
            "suggestions": [],
            "pagination": None,
        }
            
    @staticmethod
    def start_delete(
        session_id: int,
        target_record: str,
        module: Optional[str],
        client: ZohoCRMClient,
        user_query: str,
    ) -> dict:
        
        # Priority 1: Check active session context
        active_ctx = ChatSessionRepository.get_chat_session_active_context(session_id)
        active_module = active_ctx.get("active_module")
        active_id = active_ctx.get("active_record_id")
        active_name = active_ctx.get("active_record_name")
        state = CacheService.get_state(session_id)

        if not active_module:
            active_module = state.get("current_module")

        if not active_id:
            active_id = state.get("selected_record_id")

        if not active_name:
            selected = state.get("selected_record")

            if isinstance(selected, dict):
                active_name = (
                    selected.get("Name")
                    or selected.get("Full_Name")
                    or selected.get("Account_Name")
                    or selected.get("Deal_Name")
                    or selected.get("Subject")
                    or ""
                )

            elif isinstance(selected, str):
                active_name = selected

            else:
                active_name = ""
        
        use_active_context = False
        if active_id and active_module:
            if not target_record or not target_record.strip():
                use_active_context = True
            else:
                t_clean = target_record.strip().lower()
                a_clean = active_name.strip().lower()
                pronouns = [
                    "it", "its", "him", "his", "her", "them", "record", "lead", "contact", "deal", "account", 
                    "the lead", "the contact", "the deal", "the account", "the record","current",
                    "current record",
                    "selected",
                    "selected record",
                    "this lead", "this contact", "this deal", "this account", "this record"
                ]
                if t_clean in pronouns or t_clean == a_clean or (len(t_clean) >= 3 and (t_clean in a_clean or a_clean in t_clean)):
                    use_active_context = True
                else:
                    # Fetch active record to check match on other fields (company, email, etc.)
                    active_rec = None
                    state = CacheService.get_state(session_id)
                    if state.get("current_module") == active_module and state.get("cached_dataset"):
                        for rec in state.get("cached_dataset", []):
                            if str(rec.get("id")) == str(active_id):
                                active_rec = rec
                                break
                    if not active_rec and "module_cache" in state and active_module in  state.get("module_cache", {}):
                        for rec in  state.get("module_cache", {})[active_module]:
                            if str(rec.get("id")) == str(active_id):
                                active_rec = rec
                                break
                    if not active_rec:
                        try:
                            active_rec = client.get_record_by_id(active_module, active_id)
                        except Exception:
                            pass
                    
                    if active_rec:
                        match_fields = []
                        for f_key in ["Company", "Account_Name", "Email", "Phone", "Mobile"]:
                            val = active_rec.get(f_key)
                            if isinstance(val, dict):
                                match_fields.append(val.get("name") or val.get("id") or "")
                            elif val:
                                match_fields.append(str(val))
                                
                        for f_val in match_fields:
                            if f_val:
                                f_val_clean = str(f_val).strip().lower()
                                if t_clean == f_val_clean or (len(t_clean) >= 3 and (t_clean in f_val_clean or f_val_clean in t_clean)):
                                    use_active_context = True
                                    break
                    
        record = None
        module = None
        record_id = None
        record_name = None
        
        if use_active_context:
            state = CacheService.get_state(session_id)
            if state.get("current_module") == active_module and state.get("cached_dataset"):
                for rec in state.get("cached_dataset", []):
                    if str(rec.get("id")) == str(active_id):
                        record = rec
                        break
            if not record and "module_cache" in state and active_module in  state.get("module_cache", {}):
                for rec in  state.get("module_cache", {})[active_module]:
                    if str(rec.get("id")) == str(active_id):
                        record = rec
                        break
            if not record:
                try:
                    record = client.get_record_by_id(active_module, active_id)
                except Exception as e:
                    print(f"[Active Context Fetch Error]: {e}")
            if record:

                module = active_module
                record_id = active_id

                record_name = (
                    active_name
                    or SearchService.get_record_display_name(active_module, record)
                )

        # If not resolved via active context, check local cache / search Zoho
        if not record:
            if not target_record or not target_record.strip():
                res = "**Workflow State**: Awaiting Record Name\n\nPlease specify the name of the record you would like to delete."
                return DeleteService.build_response(
                    message=res,
                    module=module,
                )
            state = CacheService.get_state(session_id)
            t_lower = target_record.strip().lower()
            
            # Combine cache and Zoho search results to avoid guessing
            all_matches = []
            matched_ids = set()
            
            def add_match(mod, rec):
                r_id = rec.get("id")
                if r_id and r_id not in matched_ids:
                    matched_ids.add(r_id)
                    all_matches.append((mod, rec))

            # 1. Check current cached_dataset
            cached_module = state.get("current_module")
            cached_recs = state.get("cached_dataset", [])
            if cached_recs and cached_module:
                for rec in cached_recs:
                    name = SearchService.get_record_display_name(cached_module, rec)
                    company = rec.get("Company") or rec.get("Account_Name")
                    if isinstance(company, dict):
                        company = company.get("name")
                    company_str = str(company).lower() if company else ""
                    if t_lower in name.lower() or name.lower() in t_lower or (company_str and (t_lower in company_str or company_str in t_lower)):
                        add_match(cached_module, rec)
            
            # 2. Check historical module_cache
            module_cache = state.get("module_cache", {})
            if not isinstance(module_cache, dict):
                module_cache = {}
            for cached_mod, recs in module_cache.items():
                for rec in recs:
                    name = SearchService.get_record_display_name(cached_mod, rec)
                    company = rec.get("Company") or rec.get("Account_Name")
                    if isinstance(company, dict):
                        company = company.get("name")
                    company_str = str(company).lower() if company else ""
                    if t_lower in name.lower() or name.lower() in t_lower or (company_str and (t_lower in company_str or company_str in t_lower)):
                        add_match(cached_mod, rec)
                            
            # 3. Always search Zoho CRM to check for any other matches in CRM
            detected_module = None
            search_results = SearchService.perform_prioritized_search(client, target_record, detected_module, user_query=user_query, session_id=session_id)
            for mod, rec in search_results:
                add_match(mod, rec)
                
            cache_hits = all_matches
            
            if not cache_hits:
                res = f"I couldn't find any records matching **{target_record}** in Zoho CRM. Please verify the name or specify the module."
                return DeleteService.build_response(
                    message=res,
                    module=module,
                )
                
            # Handle Matches
            if len(cache_hits) > 1:
                matches_data = []
                display_list = []
                for idx, (mod, rec) in enumerate(cache_hits, 1):
                    name = SearchService.get_record_display_name(mod, rec)
                    matches_data.append({
                        "id": rec.get("id"),
                        "name": name,
                        "module": mod
                    })
                    lbl = SearchService.get_record_disambiguation_label(mod, rec)
                    display_list.append(f"{idx}. **{lbl}**")
                    
                serialized = json.dumps(matches_data)
                ActionRepository.create_pending_action(
                    session_id=session_id,
                    action_type="DELETE",
                    module=detected_module or "MULTIPLE",
                    record_id=None,
                    record_name=target_record,
                    old_value=serialized,
                    status="MULTIPLE_MATCHES"
                )
                options_text = "\n".join(display_list)
                res = f"### Delete Workflow\n\n**Workflow State**: Awaiting Record Selection\n\nI found multiple records matching **{target_record}**:\n\n{options_text}\n\nPlease reply with the number of the correct record."
                return DeleteService.build_response(
                    message=res,
                    module=detected_module,
                )
                
            module, record = cache_hits[0]
            record_id = record.get("id")
            record_name = SearchService.get_record_display_name(module, record)
            
        # Update session active context
        ChatSessionRepository.update_chat_session_active_context(session_id, module, record_id, record_name, last_action="delete_record")
        ActionRepository.create_pending_action(
            session_id=session_id,
            action_type="DELETE",
            module=module,
            record_id=record_id,
            record_name=record_name,
            status="AWAITING_CONFIRMATION"
        )

        res = f"""### 🗑️ Delete Record

            **Record Selected**
            • **Name:** {record_name}
            • **Module:** {module}

            ⚠️ **This action cannot be undone.**

            Are you sure you want to permanently delete this record?

            Reply with one of the following:

            ✅ **CONFIRM** — Delete the record permanently

            ❌ **CANCEL** — Keep the record
            """

        return DeleteService.build_response(
            message=res,
            module=module,
        )
    
    @staticmethod
    def handle_delete_workflow(session_id: int, user_input: str, active_action: dict, client: ZohoCRMClient) -> dict:
        
        action_id = active_action["id"]
        status = active_action["status"]
        module = active_action["module"]
        record_id = active_action["record_id"]
        record_name = active_action["record_name"]
        
        clean_input = user_input.strip().lower()
    
        
        # 1. Check expiration
        if active_action.get("expired"):
            res = "Your previous delete session has expired.\n\nPlease start the delete request again."
            return DeleteService.build_response(
                message=res,
                module=module,
            )
            
        # 2. Check for CANCEL in any state
        if clean_input in ["cancel", "no", "stop", "abort"]:
            ActionRepository.update_pending_action(action_id, status="FAILED")

            res = "Delete cancelled. Your changes have not been saved."
            return DeleteService.build_response(
                message=res,
                module=module,
            )
            
        # 3. Handle MULTIPLE_MATCHES
        if status == "MULTIPLE_MATCHES":

            try:
                matches = json.loads(active_action["old_value"])
            except Exception:
                ActionRepository.update_pending_action(action_id, status="FAILED")

                return DeleteService.build_response(
                    "Failed to load record list. Please start again.",
                    module,
                )

            if not clean_input.isdigit():

                return DeleteService.build_response(
                    f"Please reply with a number between 1 and {len(matches)}.",
                    module,
                )

            idx = int(clean_input) - 1

            if idx < 0 or idx >= len(matches):

                return DeleteService.build_response(
                    f"Please reply with a number between 1 and {len(matches)}.",
                    module,
                )

            rec = matches[idx]

            ActionRepository.update_pending_action(
                action_id,
                module=rec["module"],
                record_id=rec["id"],
                record_name=rec["name"],
                status="AWAITING_CONFIRMATION"
            )

            ChatSessionRepository.update_chat_session_active_context(
                session_id,
                rec["module"],
                rec["id"],
                rec["name"],
                last_action="delete_record"
            )

            return DeleteService.build_response(
                f"""### 🗑️ Delete Record

            **Record Selected**
            • **Name:** {rec['name']}
            • **Module:** {rec['module']}

            ⚠️ **This action cannot be undone.**

            Are you sure you want to permanently delete this record?

            Reply with:

            ✅ **CONFIRM**

            ❌ **CANCEL**
            """,
                rec["module"],
            )
            
        # 5. Handle AWAITING_CONFIRMATION
        elif status == "AWAITING_CONFIRMATION":

            if clean_input.lower() in ["confirm", "yes"]:

                ActionRepository.update_pending_action(
                    action_id,
                    status="EXECUTING"
                )

                success = client.delete_record(
                    module,
                    record_id
                )

                if success:
                    CacheService.clear_module_cache(session_id)

                    ActionRepository.update_pending_action(
                        action_id,
                        status="COMPLETED"
                    )
                    ChatSessionRepository.update_chat_session_active_context(
                        session_id,
                        None,
                        None,
                        None,
                        last_action=None
                    )

                    return DeleteService.build_response(
                        f"""✅ Record deleted successfully.

        Record:
        **{record_name}**

        Module:
        **{module}**
        """,
                        module,
                    )

                ActionRepository.update_pending_action(
                    action_id,
                    status="FAILED"
                )

                return DeleteService.build_response(
                    "Failed to delete the record from Zoho CRM.",
                    module,
                )

            elif clean_input.lower() in ["cancel", "no"]:

                ActionRepository.update_pending_action(
                    action_id,
                    status="FAILED"
                )

                return DeleteService.build_response(
                    "Delete operation cancelled.",
                    module,
                )

            else:

                return DeleteService.build_response(
                    """Please reply with

        • CONFIRM
        • CANCEL""",
                    module,
                )
                
        res = "Invalid session status. Please start your request again."
        return DeleteService.build_response(
            message=res,
            module=module,
        )