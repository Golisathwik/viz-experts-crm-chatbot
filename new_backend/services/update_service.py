import json
from typing import Optional, Tuple, List, Any
import time
from typing import Dict
from new_backend.repositories.action_repository import ActionRepository
from new_backend.repositories.chat_session_repository import ChatSessionRepository
from new_backend.crm.zoho_client import ZohoCRMClient
from new_backend.services.search_service import SearchService
from new_backend.services.cache_service import CacheService
from new_backend.services.crm_context_service import CRMContextService
from new_backend.services.create_service import CreateService
from new_backend.services.field_validation_service import FieldValidationService

# Validation Helpers
class UpdateService:
    
    @staticmethod
    def build_response(message: str, module=None):
        return {
            "operation": "update",
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
    def _get_requested_option_field(
        user_input: str,
        module: str = None,
        current_field: str = None,
    ):
        """
        Detect whether the user is asking for the allowed values
        of Lead Status or Deal Stage.

        This is intentionally rule-based so option questions
        never depend on the LLM field extractor.
        """

        text = " ".join(
            str(user_input).lower().strip().split()
        )

        # ---------------------------------------------
        # Explicit Lead Status requests
        # ---------------------------------------------
        if (
            "lead status" in text
            or "lead statuses" in text
            or "lead status options" in text
            or "lead status values" in text
            or "lead status choices" in text
        ):
            return "Lead_Status"

        # ---------------------------------------------
        # Explicit Deal Stage requests
        # ---------------------------------------------
        if (
            "deal stage" in text
            or "deal stages" in text
            or "deal stage options" in text
            or "deal stage values" in text
            or "deal stage choices" in text
        ):
            return "Stage"

        # ---------------------------------------------
        # Generic "stage" request
        # ---------------------------------------------
        if (
            "stage" in text
            and (
                "option" in text
                or "available" in text
                or "value" in text
                or "choice" in text
                or "list" in text
                or "what are" in text
                or "which" in text
            )
        ):
            return "Stage"

        # ---------------------------------------------
        # Generic "status" request
        # ---------------------------------------------
        if (
            "status" in text
            and (
                "option" in text
                or "available" in text
                or "value" in text
                or "choice" in text
                or "list" in text
                or "what are" in text
                or "which" in text
            )
        ):
            # For Leads, "status" means Lead_Status.
            if module == "Leads":
                return "Lead_Status"

            # If the current field is already Lead_Status,
            # preserve that context.
            if current_field == "Lead_Status":
                return "Lead_Status"

        # ---------------------------------------------
        # Use the active field when appropriate
        # ---------------------------------------------
        if current_field in {
            "Lead_Status",
            "Stage",
        }:
            if (
                "option" in text
                or "available" in text
                or "value" in text
                or "choice" in text
                or "list" in text
                or "what are" in text
                or "which" in text
            ):
                return current_field

        return None
            
    
    @staticmethod
    def start_update(
        session_id: int,
        target_record: str,
        raw_field: str = None,
        new_value: Optional[str] = None,
        extracted_fields: dict = None,
        client: ZohoCRMClient = None,
        user_query: str = "",
        selected_record=None,
    ) -> str:
        
        # Priority 1: Check active session context
        active_ctx = ChatSessionRepository.get_chat_session_active_context(session_id)
        active_module = active_ctx.get("active_module")
        active_id = active_ctx.get("active_record_id")
        active_name = active_ctx.get("active_record_name")
        
        # ----------------------------------------------------
        # If user mentioned a record in the update query,
        # do NOT use the active record.
        # Let the existing search flow resolve it.
        # ----------------------------------------------------

        if target_record:

            target_clean = target_record.strip().lower()

            generic_words = {
                "it",
                "its",
                "this",
                "that",
                "record",
                "lead",
                "contact",
                "account",
                "deal",
                "the record",
                "the lead",
                "the contact",
                "the account",
                "the deal",
            }

            if target_clean not in generic_words:

                # User explicitly mentioned another record.
                # Ignore the active record and use existing search flow.
                active_id = None
                active_module = None
                active_name = None
        
        use_active_context = False
        if active_id and active_module and active_name:
            if not target_record or not target_record.strip():
                use_active_context = True
            else:
                t_clean = target_record.strip().lower()
                a_clean = active_name.strip().lower()
                pronouns = [
                    "it", "its", "him", "his", "her", "them", "record", "lead", "contact", "deal", "account", 
                    "the lead", "the contact", "the deal", "the account", "the record",
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
        # Use selected record from conversation context
        if selected_record:

            state = CacheService.get_state(session_id)

            record = selected_record

            module = (
                selected_record.get("_module")
                or selected_record.get("module")
                or state.get("selected_record_module")
                or state.get("current_module")
            )
            record_id = selected_record.get("id")
            record_name = SearchService.get_record_display_name(
                module,
                selected_record,
            )
        
        if use_active_context and not selected_record:
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
                record_name = active_name

        # If not resolved via active context, check local cache / search Zoho
        if not record:
            if not target_record or not target_record.strip():
                res = "**Workflow State**: Awaiting Record Name\n\nPlease specify the name of the record you would like to update."
                return UpdateService.build_response(
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
                return UpdateService.build_response(
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
                    action_type="UPDATE",
                    module=detected_module or "MULTIPLE",
                    record_id=None,
                    record_name=target_record,
                    field_name=raw_field,
                    old_value=serialized,
                    new_value=new_value,
                    status="MULTIPLE_MATCHES"
                )
                options_text = "\n".join(display_list)
                res = f"### Update Workflow\n\n**Workflow State**: Awaiting Record Selection\n\nI found multiple records matching **{target_record}**:\n\n{options_text}\n\nPlease reply with the number of the correct record."
                return UpdateService.build_response(
                    message=res,
                    module=detected_module,
                )
                
            module, record = cache_hits[0]
            record_id = record.get("id")
            record_name = SearchService.get_record_display_name(module, record)
            
        # Update session active context
        ChatSessionRepository.update_chat_session_active_context(session_id, module, record_id, record_name, last_action="update_record")
        
        # ----------------------------------------------------
        # Resolve field/value from extracted fields first
        #
        # For selected-record updates such as:
        # "change email id to rahul2005@gmail.com"
        #
        # CreateFieldExtractor normally returns:
        # {
        #     "Email": "rahul2005@gmail.com"
        # }
        #
        # Use this as the source of truth instead of relying
        # only on QueryUnderstanding's field_name/new_value.
        # ----------------------------------------------------
        if extracted_fields:

            # Prefer the first extracted CRM field when the
            # query-understanding field is missing or generic.
            if not raw_field or raw_field.strip().lower() in {
                "field",
                "field name",
                "value",
                "email id",
                "email address",
                "email",
            }:
                extracted_field_name = next(
                    iter(extracted_fields.keys()),
                    None,
                )

                if extracted_field_name:
                    raw_field = extracted_field_name

            # If QueryUnderstanding did not provide a new value,
            # use the value extracted from the user's sentence.
            if not new_value or not str(new_value).strip():

                extracted_value = extracted_fields.get(raw_field)

                if extracted_value is None:
                    # Try case-insensitive field matching
                    for key, value in extracted_fields.items():
                        if str(key).strip().lower() == str(raw_field).strip().lower():
                            extracted_value = value
                            break

                if extracted_value is not None:
                    new_value = str(extracted_value).strip()
        
        # Field validation/parsing
        if not raw_field or not raw_field.strip():

            action_id = ActionRepository.create_pending_action(
                session_id=session_id,
                action_type="UPDATE",
                module=module,
                record_id=record_id,
                record_name=record_name,
                field_name="MULTI_FIELD_UPDATE",
                old_value="",
                new_value=json.dumps({
                    "stage": "COLLECT_FIELDS",
                    "fields": {}
                }),
                status="AWAITING_DETAILS",
            )

            summary = CreateService.build_optional_fields_prompt(
                module=module,
                collected_fields={},
                current_record=record,
            )

            return {
                "operation": "update",
                "module": module,
                "summary": summary,
                "response": summary,
                "records": [],
                "table": None,
                "chart": None,
                "kpis": None,
                "suggestions": [
                    "Continue",
                    "Cancel",
                ],
                "pagination": None,
            }
            
        # Resolve the CRM field from the normalized field name.
        clean_field = FieldValidationService.resolve_field_name(
            module,
            raw_field,
            record,
        )

        # If the direct field name could not be resolved,
        # try the extracted field keys.
        if not clean_field and extracted_fields:

            for extracted_field in extracted_fields.keys():

                clean_field = FieldValidationService.resolve_field_name(
                    module,
                    extracted_field,
                    record,
                )

                if clean_field:
                    break
                    
        if not clean_field:
            res = f"I couldn't identify the Zoho CRM field corresponding to **{raw_field}**. Please specify a valid field (e.g., Phone, Email, Status)."
            return UpdateService.build_response(
                message=res,
                module=module,
            )
            
        # Permission validation: Writable Check
        if FieldValidationService.is_read_only(clean_field):
            res = f"⚠️ Validation Error: The field **{clean_field}** is read-only and cannot be updated."
            return UpdateService.build_response(
                message=res,
                module=module,
            )
            
        # Get old value
        old_value = record.get(clean_field)
        if isinstance(old_value, dict):
            old_value = old_value.get("name") or old_value.get("id") or str(old_value)
        elif old_value is None:
            old_value = ""
        else:
            old_value = str(old_value)
            
        # Concurrency Metadata: save modified_time
        mod_time = record.get("Modified_Time")
        old_val_serialized = json.dumps({
            "value": old_value,
            "modified_time": mod_time,
            "concurrency_checked": False
        })
        
        # Create pending action
        action_id = ActionRepository.create_pending_action(
            session_id=session_id,
            action_type="UPDATE",
            module=module,
            record_id=record_id,
            record_name=record_name,
            field_name=clean_field,
            old_value=old_val_serialized,
            new_value=json.dumps({
                "stage": "COLLECT_FIELDS",
                "fields": {}
            }),
            status="AWAITING_DETAILS" if not new_value else "AWAITING_CONFIRMATION"
        )
        
        # If missing new_value, elicit it
        if not new_value or not new_value.strip():
            ActionRepository.update_pending_action(
                action_id,
                module=module,
                record_id=record_id,
                record_name=record_name,
                field_name=clean_field,
                old_value=old_val_serialized,
                status="AWAITING_DETAILS"
            )
            res = f"### Update Workflow\n\n**Workflow State**: Awaiting Field Value\n\nI found the **{record_name}** ({module[:-1]}) record. What value would you like to set for **{clean_field}**?"
            return UpdateService.build_response(
                message=res,
                module=module,
            )
            
        # Validate Inputs
        is_valid, validation_res, normalized_val = FieldValidationService.validate_field_value(clean_field, new_value)
        if not is_valid:
            ActionRepository.update_pending_action(
                action_id,
                module=module,
                record_id=record_id,
                record_name=record_name,
                field_name=clean_field,
                old_value=old_val_serialized,
                status="AWAITING_DETAILS"
            )
            res = f"**Workflow State**: Awaiting Field Value\n\n{validation_res}"
            return UpdateService.build_response(
                message=res,
                module=module,
            )
            
        # Transition to AWAITING_CONFIRMATION
        if extracted_fields:

            workflow_fields = {}

            for field, value in extracted_fields.items():

                valid, _, normalized = FieldValidationService.validate_field_value(
                    field,
                    value,
                )

                if valid:
                    workflow_fields[field] = normalized

        else:

            workflow_fields = {
                clean_field: normalized_val
            }

        workflow_data = {
            "stage": "PREVIEW",
            "fields": workflow_fields,
            "record": {
                "id": record_id,
                "module": module,
                "name": record_name,
            },
        }

        ActionRepository.update_pending_action(
            action_id,
            new_value=json.dumps(workflow_data),
            status="AWAITING_CONFIRMATION"
        )
        
        latest_record = client.get_record_by_id(
            module,
            record_id,
        )

        preview = CreateService.build_update_preview(
            module=module,
            record=latest_record,
            updated_fields=workflow_fields,
        )

        return {
            "operation": "update",
            "module": module,
            "summary": preview,
            "response": preview,
            "records": [],
            "table": None,
            "chart": None,
            "kpis": None,
            "suggestions": [
                "Confirm",
                "Add more",
                "Cancel",
            ],
            "pagination": None,
        }
        
    
    @staticmethod
    def handle_update_workflow(
        session_id,
        user_input,
        active_action,
        client,
        extracted_fields=None,
    ):
        
        action_id = active_action["id"]
        status = active_action["status"]
        module = active_action["module"]
        record_id = active_action["record_id"]
        record_name = active_action["record_name"]
        field_name = active_action["field_name"]
        old_value_serialized = active_action["old_value"]
        new_value = active_action["new_value"]
        
        clean_input = user_input.strip()
        lower_input = clean_input.lower()
        
        # Parse old value JSON and concurrency metadata
        old_value = old_value_serialized
        original_modified_time = None
        concurrency_checked = False
        if old_value_serialized and old_value_serialized.startswith("{"):
            try:
                parsed_old = json.loads(old_value_serialized)
                old_value = parsed_old.get("value", "")
                original_modified_time = parsed_old.get("modified_time")
                concurrency_checked = parsed_old.get("concurrency_checked", False)
            except Exception:
                pass
        
        # 1. Check expiration
        if active_action.get("expired"):
            res = "Your previous update session has expired.\n\nPlease start the update request again."
            return UpdateService.build_response(
                message=res,
                module=module,
            )
            
        # 2. Check for CANCEL in any state
        if lower_input in ["cancel", "no", "stop", "abort"]:
            ActionRepository.update_pending_action(action_id, status="FAILED")
            ActionRepository.log_update_audit(
                session_id=session_id,
                action_type="UPDATE",
                module=module or "Unknown",
                record_id=record_id or "Unknown",
                record_name=record_name or "Unknown",
                field_name=field_name or "Unknown",
                old_value=old_value,
                new_value=new_value or "None",
                status="CANCELLED",
                verification_result="User aborted"
            )
            res = "Update cancelled. Your changes have not been saved."
            return UpdateService.build_response(
                message=res,
                module=module,
            )
            
        # 3. Handle MULTIPLE_MATCHES
        if status == "MULTIPLE_MATCHES":
            try:
                matches = json.loads(old_value_serialized)
            except Exception:
                ActionRepository.update_pending_action(action_id, status="FAILED")
                res = "Failed to parse records list. Please start the update request again."
                return UpdateService.build_response(
                    message=res,
                    module=module,
                )
                
            selected_idx = None
            if clean_input.isdigit():
                idx = int(clean_input)
                if 1 <= idx <= len(matches):
                    selected_idx = idx - 1
            else:
                text_map = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4}
                for word, idx in text_map.items():
                    if word in lower_input and idx < len(matches):
                        selected_idx = idx
                        break
            
            if selected_idx is None:
                res = f"**Workflow State**: Awaiting Record Selection\n\nInvalid selection. Please reply with the number of the correct record (1-{len(matches)})."
                return UpdateService.build_response(
                    message=res,
                    module=module,
                )
                
            selected_rec = matches[selected_idx]
            resolved_module = selected_rec["module"]
            resolved_id = selected_rec["id"]
            resolved_name = selected_rec["name"]
            
            # Fetch record first
            try:
                record = client.get_record_by_id(resolved_module, resolved_id)
            except Exception as e:
                ActionRepository.update_pending_action(action_id, status="FAILED")
                res = f"Failed to retrieve selected record details: {str(e)}"
                return UpdateService.build_response(
                    message=res,
                    module=module,
                )
                
            if not record:
                ActionRepository.update_pending_action(action_id, status="FAILED")
                res = "Selected record does not exist in Zoho CRM."
                return UpdateService.build_response(
                    message=res,
                    module=module,
                )
                
            # Resolve Field Name
            clean_field = FieldValidationService.resolve_field_name(
                resolved_module,
                field_name,
                record,
            )
                        
            if not clean_field:
                ActionRepository.update_pending_action(action_id, status="FAILED")
                res = f"I couldn't identify the Zoho CRM field corresponding to **{field_name}**. Please start the update request again."
                return UpdateService.build_response(
                    message=res,
                    module=module,
                )
                
            # Permission validation: Writable Check
            if FieldValidationService.is_read_only(clean_field):
                ActionRepository.update_pending_action(action_id, status="FAILED")
                res = f"⚠️ Validation Error: The field **{clean_field}** is read-only and cannot be updated."
                return UpdateService.build_response(
                    message=res,
                    module=module,
                )
                
            actual_old_val = record.get(clean_field)
            if isinstance(actual_old_val, dict):
                actual_old_val = actual_old_val.get("name") or actual_old_val.get("id") or str(actual_old_val)
            elif actual_old_val is None:
                actual_old_val = ""
            else:
                actual_old_val = str(actual_old_val)
                
            ChatSessionRepository.update_chat_session_active_context(session_id, resolved_module, resolved_id, resolved_name, last_action="update_record")
 
            mod_time = record.get("Modified_Time")
            old_val_serialized = json.dumps({
                "value": actual_old_val,
                "modified_time": mod_time,
                "concurrency_checked": False
            })
 
            ActionRepository.update_pending_action(
                action_id,
                module=resolved_module,
                record_id=resolved_id,
                record_name=resolved_name,
                field_name=clean_field,
                old_value=old_val_serialized,
                status="AWAITING_DETAILS"
            )
            
            if new_value and new_value.strip():
                is_valid, validation_res, normalized_val = FieldValidationService.validate_field_value(clean_field, new_value)
                if not is_valid:
                    res = f"**Workflow State**: Awaiting Field Value\n\n{validation_res}"
                    return UpdateService.build_response(
                        message=res,
                        module=module,
                    )
                ActionRepository.update_pending_action(action_id, new_value=normalized_val, status="AWAITING_CONFIRMATION")
                res = UpdateService.generate_preview_text(resolved_module, resolved_name, clean_field, actual_old_val, normalized_val)
                return UpdateService.build_response(
                    message=res,
                    module=module,
                )
            else:
                res = f"### Update Workflow\n\n**Workflow State**: Awaiting Field Value\n\nI resolved the record to **{resolved_name}** ({resolved_module[:-1]}). What value would you like to set for **{clean_field}**?"
                return UpdateService.build_response(
                    message=res,
                    module=module,
                )
                
        # 4. Handle AWAITING_DETAILS
        elif status == "AWAITING_DETAILS":
            # ------------------------------------------
            # Cancel
            # ------------------------------------------

            if lower_input == "cancel":

                ActionRepository.update_pending_action(
                    action_id,
                    status="FAILED",
                )

                return UpdateService.build_response(
                    "Update cancelled.",
                    module,
                )


            # ------------------------------------------
            # Add More
            # ------------------------------------------

            if lower_input in ["add", "add more"]:

                try:
                    workflow = json.loads(active_action["new_value"])
                except Exception:
                    workflow = {
                        "stage": "COLLECT_FIELDS",
                        "fields": {}
                    }

                collected = workflow.get("fields", {})

                current_record = client.get_record_by_id(
                    module,
                    record_id,
                )
                print("\n===== CURRENT RECORD =====")
                print(current_record)
                print("==========================")

                return UpdateService.build_response(
                    CreateService.build_optional_fields_prompt(
                        module=module,
                        collected_fields=collected,
                        current_record=current_record,
                    ),
                    module,
                )


            # ------------------------------------------
            # Continue
            # ------------------------------------------

            if lower_input == "continue":

                try:
                    workflow = json.loads(active_action["new_value"])
                except Exception:
                    workflow = {
                        "stage": "COLLECT_FIELDS",
                        "fields": {}
                    }

                if not workflow.get("fields"):

                    return {
                        "operation": "update",
                        "module": module,
                        "summary": (
                            "Please enter at least one field before continuing.\n\n"
                            "Example:\n"
                            "• Phone 9876543210\n"
                            "• Email abc@gmail.com\n"
                            "• Industry IT"
                        ),
                        "response": (
                            "Please enter at least one field before continuing.\n\n"
                            "Example:\n"
                            "• Phone 9876543210\n"
                            "• Email abc@gmail.com\n"
                            "• Industry IT"
                        ),
                        "records": [],
                        "table": None,
                        "chart": None,
                        "kpis": None,
                        "suggestions": [
                            "Cancel"
                        ],
                        "pagination": None,
                    }

                workflow["stage"] = "PREVIEW"

                ActionRepository.update_pending_action(
                    action_id,
                    new_value=json.dumps(workflow),
                    status="AWAITING_CONFIRMATION",
                )

                record = client.get_record_by_id(
                    module,
                    record_id,
                )

                preview = CreateService.build_update_preview(
                    module=module,
                    record=record,
                    updated_fields=workflow["fields"],
                )

                return {
                    "operation": "update",
                    "module": module,
                    "summary": preview,
                    "response": preview,
                    "records": [],
                    "table": None,
                    "chart": None,
                    "kpis": None,
                    "suggestions": [
                        "Confirm",
                        "Add more",
                        "Cancel",
                    ],
                    "pagination": None,
                }


            # ------------------------------------------
            # Show available options
            # ------------------------------------------

            requested_option_field = (
                UpdateService._get_requested_option_field(
                    user_input=clean_input,
                    module=module,
                    current_field=field_name,
                )
            )

            if requested_option_field:

                options = FieldValidationService.get_available_options(
                    requested_option_field
                )

                if options:

                    label = (
                        "Lead Status"
                        if requested_option_field == "Lead_Status"
                        else "Deal Stage"
                    )

                    return UpdateService.build_response(
                        f"Available {label} values:\n\n"
                        + "\n".join(
                            f"• {x}"
                            for x in options
                        ),
                        module,
                    )

            # ------------------------------------------
            # Extracted field values (same workflow as Create)
            # ------------------------------------------

            if not extracted_fields:

                # Fallback parser for inputs like:
                # Email abc@gmail.com
                # Phone 9876543210
                # Website xyz.com

                labels = FieldValidationService.get_field_labels()

                for crm_field, label in labels.items():

                    if lower_input.startswith(label.lower()):

                        value = user_input[len(label):].strip()

                        if value:

                            extracted_fields = {
                                crm_field: value
                            }

                            break

                if not extracted_fields:

                    if field_name and field_name != "MULTI_FIELD_UPDATE":

                        extracted_fields = {
                            field_name: user_input.strip()
                        }

                    else:

                        return UpdateService.build_response(
                            "I couldn't understand the update. Please tell me the field values you want to change.",
                            module,
                        )

            try:
                workflow = json.loads(active_action["new_value"])
            except Exception:
                workflow = {
                    "stage": "COLLECT_FIELDS",
                    "fields": {}
                }

            workflow_fields = workflow.get("fields", {})
            # --------------------------------------------------
            # Fallback for MULTI_FIELD_UPDATE
            # --------------------------------------------------
            if (
                not extracted_fields
                and field_name == "MULTI_FIELD_UPDATE"
            ):

                extracted_fields = CreateService.extract_simple_field_value(
                    module=module,
                    user_text=user_input,
                ) or {}

            # --------------------------------------------------


            for field, value in extracted_fields.items():

                if isinstance(value, str):
                    value = value.strip()

                if value in ["", None]:
                    continue

                # ------------------------------------------
                # Normalize predefined CRM options
                # ------------------------------------------

                if field == "Lead_Status":
                    option_map = {
                        "attempted to contact": "Attempted to Contact",
                        "contact in future": "Contact in Future",
                        "contacted": "Contacted",
                        "junk lead": "Junk Lead",
                        "lost lead": "Lost Lead",
                        "not contacted": "Not Contacted",
                        "pre qualified": "Pre Qualified",
                        "pre-qualified": "Pre Qualified",
                    }

                    normalized_option = option_map.get(
                        str(value).strip().lower()
                    )

                    if normalized_option:
                        value = normalized_option

                elif field == "Stage":
                    option_map = {
                        "qualification": "Qualification",
                        "needs analysis": "Needs Analysis",
                        "value proposition": "Value Proposition",
                        "identify decision makers": "Identify Decision Makers",
                        "proposal/price quote": "Proposal/Price Quote",
                        "negotiation/review": "Negotiation/Review",
                        "closed won": "Closed Won",
                        "closed lost": "Closed Lost",
                        "closed lost to competition": "Closed Lost to Competition",
                    }

                    normalized_option = option_map.get(
                        str(value).strip().lower()
                    )

                    if normalized_option:
                        value = normalized_option

                valid, message, normalized = (
                    FieldValidationService.validate_field_value(
                        field,
                        value,
                    )
                )

                if not valid:
                    return UpdateService.build_response(
                        message,
                        module,
                    )

                workflow_fields[field] = normalized

                if not valid:

                    return UpdateService.build_response(
                        message,
                        module,
                    )

                workflow_fields[field] = normalized

            if not workflow_fields:

                return UpdateService.build_response(
                    "I couldn't identify any field to update.\n\n"
                    "Examples:\n"
                    "• Email abc@gmail.com\n"
                    "• Phone 9876543210\n"
                    "• Industry IT",
                    module,
                )

            workflow["fields"] = workflow_fields

            # Stay in field collection mode.
            # Only Continue should move to Preview.
            workflow["stage"] = "COLLECT_FIELDS"

            ActionRepository.update_pending_action(
                action_id,
                new_value=json.dumps(workflow),
                status="AWAITING_DETAILS",
            )

            record = client.get_record_by_id(
                module,
                record_id,
            )

            summary = CreateService.build_optional_fields_prompt(
                module=module,
                collected_fields=workflow_fields,
                current_record=record,
            )

            return {
                "operation": "update",
                "module": module,
                "summary": summary,
                "response": summary,
                "records": [],
                "table": None,
                "chart": None,
                "kpis": None,
                "suggestions": [
                    "Continue",
                    "Cancel",
                ],
                "pagination": None,
            }
            
        # 5. Handle AWAITING_CONFIRMATION
        elif status == "AWAITING_CONFIRMATION":
            # ------------------------------------------
            # Show available options from Preview
            # ------------------------------------------

            try:
                preview_workflow = json.loads(
                    active_action.get("new_value") or "{}"
                )
            except Exception:
                preview_workflow = {}

            preview_fields = preview_workflow.get(
                "fields",
                {}
            )

            requested_option_field = (
                UpdateService._get_requested_option_field(
                    user_input=clean_input,
                    module=module,
                    current_field=field_name,
                )
            )

            # If the user asks about options while previewing
            # a Lead_Status or Stage update, answer the question
            # without leaving the preview state.
            if requested_option_field:

                options = FieldValidationService.get_available_options(
                    requested_option_field
                )

                if options:

                    label = (
                        "Lead Status"
                        if requested_option_field == "Lead_Status"
                        else "Deal Stage"
                    )

                    return UpdateService.build_response(
                        f"Available {label} values:\n\n"
                        + "\n".join(
                            f"• {x}"
                            for x in options
                        )
                        + "\n\n"
                        "Your update preview is still active.",
                        module,
                    )
            
            if lower_input in [
                "add more",
                "add",
                "edit",
                "modify",
            ]:

                try:
                    workflow = json.loads(active_action["new_value"])
                except Exception:
                    workflow = {
                        "stage": "COLLECT_FIELDS",
                        "fields": {}
                    }

                workflow["stage"] = "COLLECT_FIELDS"

                ActionRepository.update_pending_action(
                    action_id,
                    new_value=json.dumps(workflow),
                    status="AWAITING_DETAILS",
                )

                workflow_fields = workflow.get("fields", {})

                current_record = client.get_record_by_id(
                    module,
                    record_id,
                )
                
                print("\n===== CURRENT RECORD =====")
                print(current_record)
                print("==========================")

                summary = CreateService.build_optional_fields_prompt(
                    module=module,
                    collected_fields=workflow_fields,
                    current_record=current_record,
                )

                return {
                    "operation": "update",
                    "module": module,
                    "summary": summary,
                    "response": summary,
                    "records": [],
                    "table": None,
                    "chart": None,
                    "kpis": None,
                    "suggestions": [
                        "Continue",
                        "Cancel",
                    ],
                    "pagination": None,
                }
            if lower_input in ["confirm","continue", "yes", "go ahead", "approve", "do it"]:
                # Optimistic Concurrency Protection check
                fresh_record = None
                try:
                    fresh_record = client.get_record_by_id(module, record_id)
                except Exception as e:
                    print(f"[Concurrency Check Fetch Error]: {e}")
                    
                if fresh_record and original_modified_time and not concurrency_checked:
                    current_modified_time = fresh_record.get("Modified_Time")
                    if current_modified_time and current_modified_time != original_modified_time:
                        updated_old_serialized = json.dumps({
                            "value": old_value,
                            "modified_time": current_modified_time,
                            "concurrency_checked": True
                        })
                        ActionRepository.update_pending_action(action_id, old_value=updated_old_serialized)
                        res = (
                            f"⚠️ **Optimistic Concurrency Conflict**\n\n"
                            f"This record was modified by another user since you loaded it.\n"
                            f"- Original Modified Time: `{original_modified_time}`\n"
                            f"- Current Modified Time: `{current_modified_time}`\n\n"
                            f"Do you still want to overwrite these changes? Type **CONFIRM** to proceed anyway, or **CANCEL** to abort."
                        )
                        return UpdateService.build_response(
                            message=res,
                            module=module,
                        )
                
                ActionRepository.update_pending_action(action_id, status="EXECUTING")
                try:
                    workflow = json.loads(active_action["new_value"])
                except Exception:
                    workflow = {
                        "stage": "COLLECT_FIELDS",
                        "fields": {}
                    }

                fields = workflow.get("fields", {})

                success = True

                for field, value in fields.items():

                    ok = client.update_record(
                        module,
                        record_id,
                        field,
                        value,
                    )

                    if not ok:
                        success = False
                        break
                if success:
                    fresh_record = client.get_record_by_id(
                        module,
                        record_id,
                    )
                        
                    # Mark it completed because Zoho API itself returned success!
                    ActionRepository.update_pending_action(action_id, status="COMPLETED")
                    ChatSessionRepository.update_chat_session_active_context(session_id, module, record_id, record_name, last_action="update_record")
                    
                    verification_passed = True

                    for field, value in fields.items():

                        actual = fresh_record.get(field)

                        if isinstance(actual, dict):
                            actual = actual.get("name")

                        if not FieldValidationService.verify_values_match(
                            actual,
                            value,
                        ):
                            verification_passed = False
                            break
                    
                    # Audit log
                    ActionRepository.log_update_audit(
                        session_id=session_id,
                        action_type="UPDATE",
                        module=module,
                        record_id=record_id,
                        record_name=record_name,
                        field_name=field_name,
                        old_value=old_value,
                        new_value=new_value,
                        user_id=None,
                        status="SUCCESS",
                        verification_result="Passed" if verification_passed else "Passed (API Confirmed)"
                    )
                    
                    if fresh_record:
                        # Sync Cache
                        CRMContextService.sync_cache_record(session_id, module, record_id, fresh_record)
                        state = CacheService.get_state(session_id)

                        state["selected_record"] = fresh_record
                        state["selected_record_id"] = record_id
                        state["selected_record_data"] = fresh_record
                        
                    
                    summary = CreateService.build_success_summary(
                        module,
                        fields,
                        verification_passed,
                    )

                    return UpdateService.build_response(
                        message=summary,
                        module=module,
                    )
                else:
                    ActionRepository.update_pending_action(action_id, status="FAILED")
                    ActionRepository.log_update_audit(session_id, "UPDATE", module, record_id, record_name, field_name, old_value, new_value, None, "FAILED", "Zoho update API failed")
                    res = f"Failed to update record **{record_name}** in Zoho CRM. Please check connection and try again."
                    return UpdateService.build_response(
                        message=res,
                        module=module,
                    )
                    
            elif lower_input in ["show current record", "show record", "inspect"]:
                record = client.get_record_by_id(module, record_id)
                if not record:
                    res = f"Couldn't load current fields for **{record_name}** from Zoho CRM."
                    return UpdateService.build_response(
                        message=res,
                        module=module,
                    )
                    
                display_fields = ["id", "First_Name", "Last_Name", "Account_Name", "Deal_Name", "Email", "Phone", "Mobile", "Website", "Lead_Status", "Stage", "Amount", "Annual_Revenue", "No_of_Employees", "Probability", "Closing_Date"]
                table_lines = [
                    "**Workflow State**: Awaiting Confirmation\n",
                    "### Current Record Details\n",
                    "| Field | Value |",
                    "| --- | --- |"
                ]
                for f in display_fields:
                    if f in record:
                        val = record[f]
                        if isinstance(val, dict):
                            val = val.get("name") or val.get("id") or str(val)
                        if val is not None and str(val).strip():
                            label = f.replace("_", " ")
                            table_lines.append(f"| {label} | {val} |")
                
                table_lines.append("\nPlease choose:")
                table_lines.append("- Type **CONFIRM** to proceed with the update.")
                table_lines.append("- Type **CANCEL** to abort the request.")
                
                ActionRepository.update_pending_action(action_id)
                res = "\n".join(table_lines)
                return UpdateService.build_response(
                    message=res,
                    module=module,
                )
                
            else:

                try:
                    workflow = json.loads(active_action["new_value"])
                except Exception:
                    workflow = {
                        "stage": "COLLECT_FIELDS",
                        "fields": {}
                    }

                workflow["stage"] = "COLLECT_FIELDS"

                ActionRepository.update_pending_action(
                    action_id,
                    new_value=json.dumps(workflow),
                    status="AWAITING_DETAILS",
                )

                try:
                    current_record = client.get_record_by_id(
                        module,
                        record_id,
                    )
                except Exception:
                    current_record = {}

                workflow_fields = workflow.get("fields", {})

                return UpdateService.build_response(
                    CreateService.build_optional_fields_prompt(
                        module=module,
                        collected_fields=workflow_fields,
                        current_record=current_record,
                    ),
                    module,
                )
                
        res = "Invalid session status. Please start your request again."
        return UpdateService.build_response(
            message=res,
            module=module,
        )
    