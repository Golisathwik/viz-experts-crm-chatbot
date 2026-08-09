from typing import Dict, Any
import json
from new_backend.services.read_service import ReadService
from new_backend.services.crm_service import CRMService
from new_backend.services.response_service import ResponseService
from new_backend.services.navigation_service import NavigationService
from new_backend.services.cache_service import CacheService
from new_backend.repositories.chat_repository import ChatRepository
from new_backend.ai.response_generation import ResponseGeneration
# from new_backend.ai.update_field_extractor import UpdateFieldExtractor
from new_backend.ai.query_understanding import QueryUnderstanding
from new_backend.ai.create_field_extractor import CreateFieldExtractor
from new_backend.repositories.action_repository import ActionRepository
from new_backend.services.create_service import CreateService
from new_backend.services.update_service import UpdateService
from new_backend.services.field_validation_service import FieldValidationService
from new_backend.services.create_workflow_service import CreateWorkflowService

class ConversationController:

    async def process_message(
        self,
        crm_service: CRMService,
        user_id: int,
        session_id: int,
        prompt: str,
        history=None,
        file_context: str = "",
        api_keys=None,
    ):

        read_service = ReadService(crm_service)
        response_service = ResponseService()

        history = history or []
        api_keys = api_keys or {}
        state = CacheService.get_state(session_id)
        print("\n===== SESSION STATE =====")
        print(state)
        print("=========================\n")
        
        # --------------------------------------------------
        # GLOBAL CRM FIELD OPTIONS
        # --------------------------------------------------
        # Handle explicit questions such as:
        # "What are the available options for deal stage?"
        # "What are the available options for lead status?"
        #
        # IMPORTANT:
        # This must run BEFORE QueryUnderstanding so that
        # the question is not treated as a normal search.
        # --------------------------------------------------

        lower_prompt = prompt.strip().lower()

        is_option_question = (
            (
                "option" in lower_prompt
                or "options" in lower_prompt
                or "available" in lower_prompt
                or "values" in lower_prompt
                or "choices" in lower_prompt
                or "list" in lower_prompt
                or "what are" in lower_prompt
                or "which" in lower_prompt
            )
            and
            (
                "status" in lower_prompt
                or "stage" in lower_prompt
            )
        )

        if is_option_question:

            # ----------------------------------------------
            # Determine the requested CRM field
            # ----------------------------------------------

            option_field = None
            option_module = state.get("current_module")

            # Deal Stage
            if "stage" in lower_prompt:
                option_field = "Stage"

            # Lead Status
            elif "status" in lower_prompt:
                if option_module == "Leads":
                    option_field = "Lead_Status"

            # ----------------------------------------------
            # Return available options
            # ----------------------------------------------

            if option_field:

                options = (
                    FieldValidationService.get_available_options(
                        option_field
                    )
                )

                if options:

                    label = (
                        "Deal Stage"
                        if option_field == "Stage"
                        else "Lead Status"
                    )

                    summary = (
                        f"### Available {label} Options\n\n"
                        + "\n".join(
                            f"• {option}"
                            for option in options
                        )
                    )

                    # Do NOT modify the pending CREATE/UPDATE
                    # workflow state. The user is only asking
                    # for information.

                    response = {
                        "summary": summary,
                        "kpis": None,
                        "table": None,
                        "chart": None,
                        "suggestions": [
                            "Continue",
                            "Add more",
                            "Cancel",
                        ],
                    }

                    ChatRepository.save_chat_message(
                        session_id=session_id,
                        role="user",
                        message=prompt,
                    )

                    ChatRepository.save_chat_message(
                        session_id=session_id,
                        role="assistant",
                        message=summary,
                        response_json=json.dumps(response),
                    )

                    return {
                        "success": True,
                        "operation": "show_field_options",
                        "module": option_module,
                        "response": response,
                        "records": [],
                        "table": None,
                        "chart": None,
                        "kpis": None,
                        "summary": summary,
                        "suggestions": response["suggestions"],
                        "pagination": None,
                        "query": {},
                    }
        
        # --------------------------------------------------
        # Pending Update Workflow
        # --------------------------------------------------
        # IMPORTANT:
        # Handle an active UPDATE before QueryUnderstanding.
        # This prevents values such as "lost lead" from being
        # interpreted as a new search query.
        # --------------------------------------------------

        active_action = ActionRepository.get_active_pending_action(session_id)

        if (
            active_action
            and active_action.get("action_type") == "UPDATE"
        ):

            try:
                workflow = json.loads(
                    active_action.get("new_value") or "{}"
                )
            except Exception:
                workflow = {
                    "stage": "COLLECT_FIELDS",
                    "fields": {}
                }

            stage = workflow.get(
                "stage",
                "COLLECT_FIELDS"
            )

            lower_prompt = prompt.strip().lower()
            extracted = {}

            # --------------------------------------------
            # Detect option-list questions
            # --------------------------------------------

            is_option_question = (
                (
                    "option" in lower_prompt
                    or "options" in lower_prompt
                    or "available" in lower_prompt
                    or "values" in lower_prompt
                    or "choices" in lower_prompt
                    or "list" in lower_prompt
                    or "what are" in lower_prompt
                )
                and
                (
                    "status" in lower_prompt
                    or "stage" in lower_prompt
                )
            )

            # --------------------------------------------
            # Extract update fields
            # --------------------------------------------

            if (
                stage == "COLLECT_FIELDS"
                and not is_option_question
                and lower_prompt not in [
                    "continue",
                    "confirm",
                    "yes",
                    "ok",
                    "okay",
                    "cancel",
                    "add more",
                    "add more fields",
                ]
            ):

                extracted = await CreateFieldExtractor.extract_fields(
                    module=active_action["module"],
                    user_text=prompt,
                    api_keys=api_keys,
                ) or {}

                # --------------------------------------------
                # Fallback for Multi Field Update
                # --------------------------------------------

                if (
                    not extracted
                    and active_action.get("field_name")
                    == "MULTI_FIELD_UPDATE"
                ):

                    extracted = (
                        CreateService.extract_simple_field_value(
                            module=active_action["module"],
                            user_text=prompt,
                        )
                        or {}
                    )

                # --------------------------------------------
                # Single-field fallback
                # --------------------------------------------

                if (
                    not extracted
                    and active_action.get("field_name")
                    and active_action.get("field_name")
                    != "MULTI_FIELD_UPDATE"
                ):

                    extracted = {
                        active_action["field_name"]:
                        prompt.strip()
                    }

            response = UpdateService.handle_update_workflow(
                session_id=session_id,
                user_input=prompt,
                active_action=active_action,
                client=crm_service.client,
                extracted_fields=extracted,
            )

            ChatRepository.save_chat_message(
                session_id=session_id,
                role="user",
                message=prompt,
            )

            assistant_message = (
                response.get("response")
                or response.get("summary")
                or ""
            ) if isinstance(response, dict) else str(response)

            ChatRepository.save_chat_message(
                session_id=session_id,
                role="assistant",
                message=assistant_message,
                response_json=json.dumps(response),
            )

            return {
                "success": True,
                "operation": response.get("operation"),
                "module": response.get("module"),
                "response": response,
                "records": response.get("records", []),
                "table": response.get("table"),
                "chart": response.get("chart"),
                "kpis": response.get("kpis"),
                "summary": response.get("summary") or response.get("response"),
                "suggestions": response.get("suggestions", []),
                "pagination": response.get("pagination"),
                "query": {},
            }
        # --------------------------------------------------
        # Selected Record Follow-up
        # --------------------------------------------------
        print("=" * 60)
        print("ENTERING QUERY UNDERSTANDING")
        print("PROMPT =", prompt)
        print("=" * 60)
        understanding = QueryUnderstanding.understand_query(
            prompt,
            current_module=state.get("current_module")
        )
        print("=" * 60)
        print("UNDERSTANDING =", understanding)
        print("=" * 60)

        if (
            understanding["operation"] == "selected_record_field"
            and state.get("selected_record")
        ):

            record = state["selected_record"]

            field = understanding["search"]["field"]

            value = (
                record.get(field)
                or record.get(field.lower())
                or record.get(field.upper())
            )

            if isinstance(value, dict):
                value = value.get("name", value)

            if value in ("", None, [], {}):
                value = "Not available"

            response = {
                "summary": f"**{field.replace('_',' ')}**\n\n{value}",
                "kpis": None,
                "table": None,
                "chart": None,
                "suggestions": [
                    "Show phone",
                    "Show email",
                    "Show company",
                    "Show status",
                ],
            }

            ChatRepository.save_chat_message(
                session_id=session_id,
                role="user",
                message=prompt,
            )

            ChatRepository.save_chat_message(
                session_id=session_id,
                role="assistant",
                message=response["summary"],
                response_json=json.dumps(response),
            )

            return {
                "success": True,
                "operation": "selected_record_field",
                "module": state["current_module"],
                "response": response,
                "records": [],
                "table": None,
                "chart": None,
                "kpis": None,
                "summary": response["summary"],
                "suggestions": response["suggestions"],
                "pagination": None,
                "query": {},
            }
        
        # --------------------------------------------------
        # Pending Update
        # --------------------------------------------------

        if state.get("pending_update"):

            pending = state["pending_update"]
            lower_prompt = prompt.lower().strip()

            if any(
                word in lower_prompt
                for word in [
                    "option",
                    "options",
                    "available",
                    "values",
                    "choices",
                    "list",
                    "show them",
                    "what are"
                ]
            ):
                crm_result = {
                    "operation": "show_field_options",
                    "module": state.get("current_module"),
                    "records": [],
                    "summary": None,
                    "table": None,
                    "chart": None,
                    "kpis": None,
                    "suggestions": []
                }

                response = await response_service.generate_response(
                    query=prompt,
                    crm_result=crm_result,
                    history=history,
                    session_id=session_id,
                    api_keys=api_keys,
                )
                summary = (
                    response.get("summary")
                    if isinstance(response, dict)
                    else response
                )

                suggestions = (
                    response.get("suggestions", [])
                    if isinstance(response, dict)
                    else []
                )

                return {
                    "success": True,
                    "operation": "show_field_options",
                    "module": state.get("current_module"),
                    "response": response,
                    "records": [],
                    "table": None,
                    "chart": None,
                    "kpis": None,
                    "summary": summary,
                    "suggestions": suggestions,
                    "pagination": None,
                    "query": {},
                }

            update_query = (
                f"update {pending['field_name']} "
                f"to {prompt.strip()}"
            )

            state["pending_update"] = None

            crm_result = await read_service.execute(
                query=update_query,
                session_id=session_id,
                api_keys=api_keys,
                current_module=state.get("current_module"),
            )
            if crm_result.get("module"):
                state["current_module"] = crm_result["module"]

            response = await response_service.generate_response(
                query=update_query,
                crm_result=crm_result,
                history=history,
                session_id=session_id,
                api_keys=api_keys,
            )

            ChatRepository.save_chat_message(
                session_id=session_id,
                role="user",
                message=prompt,
            )

            assistant_message = (
                response.get("summary", "")
                if isinstance(response, dict)
                else response
            )

            ChatRepository.save_chat_message(
                session_id=session_id,
                role="assistant",
                message=assistant_message,
                response_json=json.dumps(response),
            )

            return {
                "success": True,
                "operation": crm_result.get("operation"),
                "module": crm_result.get("module"),
                "response": response,
                "records": crm_result.get("records", []),
                "table": crm_result.get("table"),
                "chart": crm_result.get("chart"),
                "kpis": crm_result.get("kpis"),
                "summary": response.get("summary"),
                "suggestions": response.get("suggestions", []),
                "pagination": crm_result.get("pagination"),
                "query": crm_result.get("query"),
            }
        
        # --------------------------------------------------
        # Pending Create Workflow
        # --------------------------------------------------

        active_action = ActionRepository.get_active_pending_action(session_id)

        if (
            active_action
            and active_action["action_type"] == "CREATE"
        ):
            lower_prompt = prompt.strip().lower()
            
            # ---------------------------------------
            # Load current create workflow state
            # ---------------------------------------

            try:
                workflow_state = json.loads(active_action.get("new_value") or "{}")
            except Exception:
                workflow_state = {}

            stage = workflow_state.get("stage", "REQUIRED_FIELDS")
            
            understanding = QueryUnderstanding.understand_query(
                prompt,
                current_module=state.get("current_module")
            )

            if (
                understanding.get("operation") == "create"
                and stage != "PREVIEW"
            ):
                response = {
                    "summary": (
                        f"You already have a Create {active_action['module'][:-1]} workflow in progress.\n\n"
                        "Please complete or cancel the current workflow first.\n\n"
                        "Available options:\n"
                        "• Continue\n"
                        "• Add more\n"
                        "• Cancel"
                    ),
                    "kpis": None,
                    "table": None,
                    "chart": None,
                    "suggestions": [
                        "Continue",
                        "Add more",
                        "Cancel",
                    ],
                }

                return {
                    "success": True,
                    "operation": "create",
                    "module": active_action["module"],
                    "response": response,
                    "records": [],
                    "table": None,
                    "chart": None,
                    "kpis": None,
                    "summary": response["summary"],
                    "suggestions": response["suggestions"],
                    "pagination": None,
                    "query": {},
                }

            result = CreateService.handle_create_workflow(
                session_id=session_id,
                user_input=prompt,
                active_action=active_action,
                client=crm_service.client,
            )

            if result["status"] == "CANCELLED":

                response = {
                    "summary": result["message"],
                    "kpis": None,
                    "table": None,
                    "chart": None,
                    "suggestions": [],
                }

                ChatRepository.save_chat_message(
                    session_id=session_id,
                    role="user",
                    message=prompt,
                )

                ChatRepository.save_chat_message(
                    session_id=session_id,
                    role="assistant",
                    message=response["summary"],
                    response_json=json.dumps(response),
                )

                return {
                    "success": True,
                    "operation": "create",
                    "module": result["module"],
                    "response": response,
                    "records": [],
                    "table": None,
                    "chart": None,
                    "kpis": None,
                    "summary": response["summary"],
                    "suggestions": [],
                    "pagination": None,
                    "query": {},
                }
                
            # ---------------------------------------
            # PREVIEW STAGE
            # ---------------------------------------

            if stage == "PREVIEW":
                # --------------------------------------------------
                # CREATE PREVIEW: Available field options
                # IMPORTANT:
                # Handle option questions BEFORE field extraction.
                # Otherwise the extractor may save the option list
                # as the actual field value.
                # --------------------------------------------------

                is_option_question = (
                    (
                        "option" in lower_prompt
                        or "options" in lower_prompt
                        or "available" in lower_prompt
                        or "values" in lower_prompt
                        or "choices" in lower_prompt
                        or "list" in lower_prompt
                        or "what are" in lower_prompt
                    )
                    and
                    (
                        "status" in lower_prompt
                        or "stage" in lower_prompt
                    )
                )

                if is_option_question:

                    option_field = None

                    if "status" in lower_prompt:
                        option_field = "Lead_Status"

                    elif "stage" in lower_prompt:
                        option_field = "Stage"

                    if option_field:

                        options = FieldValidationService.get_available_options(
                            option_field
                        )

                        if options:

                            label = (
                                "Lead Status"
                                if option_field == "Lead_Status"
                                else "Deal Stage"
                            )

                            response = {
                                "summary": (
                                    f"Available {label} values:\n\n"
                                    + "\n".join(
                                        f"• {value}"
                                        for value in options
                                    )
                                ),
                                "kpis": None,
                                "table": None,
                                "chart": None,
                                "suggestions": [
                                    "Continue",
                                    "Add more",
                                    "Cancel",
                                ],
                            }

                            ChatRepository.save_chat_message(
                                session_id=session_id,
                                role="user",
                                message=prompt,
                            )

                            ChatRepository.save_chat_message(
                                session_id=session_id,
                                role="assistant",
                                message=response["summary"],
                                response_json=json.dumps(response),
                            )

                            return {
                                "success": True,
                                "operation": "create",
                                "module": active_action["module"],
                                "response": response,
                                "records": [],
                                "table": None,
                                "chart": None,
                                "kpis": None,
                                "summary": response["summary"],
                                "suggestions": response["suggestions"],
                                "pagination": None,
                                "query": {},
                            }

                if lower_prompt in [
                    "continue",
                    "yes",
                    "ok",
                    "okay",
                    "proceed",
                    "go ahead",
                    "create",
                    "create it",
                    "submit",
                ]:

                    response = CreateService.confirm_create(
                        active_action=active_action,
                        crm_service=crm_service,
                    )

                    ChatRepository.save_chat_message(
                        session_id=session_id,
                        role="user",
                        message=prompt,
                    )

                    ChatRepository.save_chat_message(
                        session_id=session_id,
                        role="assistant",
                        message=response["summary"],
                        response_json=json.dumps(response),
                    )

                    return {
                        "success": True,
                        "operation": "create",
                        "module": active_action["module"],
                        "response": response,
                        "records": [],
                        "table": None,
                        "chart": None,
                        "kpis": None,
                        "summary": response["summary"],
                        "suggestions": response.get("suggestions", []),
                        "pagination": None,
                        "query": {},
                    }
                    

                if lower_prompt in [
                    "add more",
                    "more",
                    "edit",
                    "modify",
                    "update",
                ]:

                    workflow_state["stage"] = "OPTIONAL_FIELDS"

                    ActionRepository.update_pending_action(
                        action_id=active_action["id"],
                        new_value=json.dumps(workflow_state),
                    )
                    fields = workflow_state.get("fields", {})

                    summary = CreateService.build_optional_fields_prompt(
                        active_action["module"],
                        fields,
                    )

                    response = {
                        "summary": summary,
                        "kpis": None,
                        "table": None,
                        "chart": None,
                        "suggestions": [
                            "Continue",
                            "Cancel",
                        ],
                    }

                    ChatRepository.save_chat_message(
                        session_id=session_id,
                        role="user",
                        message=prompt,
                    )

                    ChatRepository.save_chat_message(
                        session_id=session_id,
                        role="assistant",
                        message=response["summary"],
                        response_json=json.dumps(response),
                    )

                    return {
                        "success": True,
                        "operation": "create",
                        "module": active_action["module"],
                        "response": response,
                        "records": [],
                        "table": None,
                        "chart": None,
                        "kpis": None,
                        "summary": response["summary"],
                        "suggestions": response["suggestions"],
                        "pagination": None,
                        "query": {},
                    }
                    
                # ---------------------------------------
                # User edited preview fields
                # ---------------------------------------

                extracted = await CreateService.extract_fields(
                    module=active_action["module"],
                    prompt=prompt,
                    api_keys=api_keys,
                )

                if extracted:

                    result = CreateService.update_preview_fields(
                        active_action=active_action,
                        extracted=extracted,
                    )

                    if not result["success"]:

                        response = {
                            "summary": result["summary"],
                            "kpis": None,
                            "table": None,
                            "chart": None,
                            "suggestions": [],
                        }

                    else:

                        summary = CreateService.build_preview(
                            active_action["module"],
                            result["fields"],
                        )

                        response = {
                            "summary": summary,
                            "kpis": None,
                            "table": None,
                            "chart": None,
                            "suggestions": [
                                "Continue",
                                "Add more",
                                "Cancel",
                            ],
                        }

                    ChatRepository.save_chat_message(
                        session_id=session_id,
                        role="user",
                        message=prompt,
                    )

                    ChatRepository.save_chat_message(
                        session_id=session_id,
                        role="assistant",
                        message=response["summary"],
                        response_json=json.dumps(response),
                    )

                    return {
                        "success": True,
                        "operation": "create",
                        "module": active_action["module"],
                        "response": response,
                        "records": [],
                        "table": None,
                        "chart": None,
                        "kpis": None,
                        "summary": response["summary"],
                        "suggestions": response.get("suggestions", []),
                        "pagination": None,
                        "query": {},
                    }
            # PREVIEW block ends here
            if stage in ["REQUIRED_FIELDS", "OPTIONAL_FIELDS"]:

                # --------------------------------------------------
                # CREATE: Available field options
                # Reuse the same detection style as UPDATE.
                # Do NOT extract this question as CRM field data.
                # --------------------------------------------------

                is_option_question = (
                    (
                        "option" in lower_prompt
                        or "options" in lower_prompt
                        or "available" in lower_prompt
                        or "values" in lower_prompt
                        or "choices" in lower_prompt
                        or "list" in lower_prompt
                        or "what are" in lower_prompt
                    )
                    and
                    (
                        "status" in lower_prompt
                        or "stage" in lower_prompt
                    )
                )

                if is_option_question:

                    option_field = None

                    # Lead Status
                    if "status" in lower_prompt:
                        option_field = "Lead_Status"

                    # Deal Stage
                    elif "stage" in lower_prompt:
                        option_field = "Stage"

                    if option_field:

                        options = FieldValidationService.get_available_options(
                            option_field
                        )

                        if options:

                            label = (
                                "Lead Status"
                                if option_field == "Lead_Status"
                                else "Deal Stage"
                            )

                            response = {
                                "summary": (
                                    f"Available {label} values:\n\n"
                                    + "\n".join(
                                        f"• {value}"
                                        for value in options
                                    )
                                ),
                                "kpis": None,
                                "table": None,
                                "chart": None,
                                "suggestions": [
                                    "Continue",
                                    "Add more",
                                    "Cancel",
                                ],
                            }

                            return {
                                "success": True,
                                "operation": "create",
                                "module": active_action["module"],
                                "response": response,
                                "records": [],
                                "table": None,
                                "chart": None,
                                "kpis": None,
                                "summary": response["summary"],
                                "suggestions": response["suggestions"],
                                "pagination": None,
                                "query": {},
                            }
            
            extracted = {}

            if (
                stage in ["REQUIRED_FIELDS", "OPTIONAL_FIELDS"]
                and lower_prompt not in [
                    "continue",
                    "confirm",
                    "yes",
                    "ok",
                    "okay",
                    "cancel",
                    "add more",
                ]
            ):

                extracted = await CreateService.extract_fields(
                    active_action["module"],
                    prompt,
                    api_keys,
                )
            
            if stage == "OPTIONAL_FIELDS" and lower_prompt == "continue":

                workflow_state["stage"] = "PREVIEW"

                ActionRepository.update_pending_action(
                    action_id=active_action["id"],
                    new_value=json.dumps(workflow_state),
                )

                active_action = ActionRepository.get_active_pending_action(session_id)

                workflow_state = json.loads(
                    active_action["new_value"]
                )

                response = {
                    "summary": CreateService.build_preview(
                        active_action["module"],
                        workflow_state["fields"],
                    ),
                    "kpis": None,
                    "table": None,
                    "chart": None,
                    "suggestions": [
                        "Continue",
                        "Add more",
                        "Cancel",
                    ],
                }

                return {
                    "success": True,
                    "operation": "create",
                    "module": active_action["module"],
                    "response": response,
                    "records": [],
                    "table": None,
                    "chart": None,
                    "kpis": None,
                    "summary": response["summary"],
                    "suggestions": response["suggestions"],
                    "pagination": None,
                    "query": {},
                }

            print("\n===== EXTRACTED FIELDS =====")
            print(extracted)
            print("============================\n")

            if not extracted:

                response = {
                    "summary": (
                        "I couldn't identify any CRM fields.\n\n"
                        "Please provide the record details again."
                    ),
                    "kpis": None,
                    "table": None,
                    "chart": None,
                    "suggestions": [],
                }

            else:

                result = CreateService.process_collected_fields(
                    active_action=active_action,
                    extracted=extracted,
                )

                if not result["success"]:

                    response = {
                        "summary": result["summary"],
                        "kpis": None,
                        "table": None,
                        "chart": None,
                        "suggestions": [],
                    }

                else:

                    fields = result["fields"]

                    if result["complete"]:

                        response = {
                            "summary": CreateService.build_preview(
                                active_action["module"],
                                fields,
                            ),
                            "kpis": None,
                            "table": None,
                            "chart": None,
                            "suggestions": [
                                "Continue",
                                "Add more",
                                "Cancel",
                            ],
                        }

                    else:

                        validation = CreateService.build_missing_fields_response(
                            active_action["module"],
                            fields,
                        )

                        response = {
                            "summary": validation["summary"],
                            "kpis": None,
                            "table": None,
                            "chart": None,
                            "suggestions": [],
                        }

            ChatRepository.save_chat_message(
                session_id=session_id,
                role="user",
                message=prompt,
            )

            ChatRepository.save_chat_message(
                session_id=session_id,
                role="assistant",
                message=response["summary"],
                response_json=json.dumps(response),
            )

            return {
                "success": True,
                "operation": "create",
                "module": active_action["module"],
                "response": response,
                "records": [],
                "table": None,
                "chart": None,
                "kpis": None,
                "summary": response["summary"],
                "suggestions": [],
                "pagination": None,
                "query": {},
            }
            
        # --------------------------------------------------
        # Pending Update Workflow
        # --------------------------------------------------

        # active_action = ActionRepository.get_active_pending_action(session_id)

        # if (
        #     active_action
        #     and active_action["action_type"] == "UPDATE"
        # ):

        #     workflow = json.loads(active_action.get("new_value") or "{}")

        #     stage = workflow.get("stage", "COLLECT_FIELDS")

        #     lower_prompt = prompt.strip().lower()

        #     extracted = {}

        #     # --------------------------------------------
        #     # Detect option-list questions
        #     # --------------------------------------------

        #     is_option_question = (
        #         "option" in lower_prompt
        #         or "options" in lower_prompt
        #         or "available" in lower_prompt
        #         or "values" in lower_prompt
        #         or "choices" in lower_prompt
        #         or "list" in lower_prompt
        #     ) and (
        #         "status" in lower_prompt
        #         or "stage" in lower_prompt
        #     )

        #     # --------------------------------------------
        #     # Don't extract fields for workflow commands
        #     # or option-list questions.
        #     # --------------------------------------------

        #     if (
        #         stage == "COLLECT_FIELDS"
        #         and not is_option_question
        #         and lower_prompt not in [
        #             "continue",
        #             "confirm",
        #             "yes",
        #             "ok",
        #             "okay",
        #             "cancel",
        #             "add more",
        #             "add more fields",
        #         ]
        #     ):

        #         extracted = await CreateService.extract_fields(
        #             module=active_action["module"],
        #             prompt=prompt,
        #             api_keys=api_keys,
        #         ) or {}

        #         # --------------------------------------------
        #         # Fallback for Multi Field Update
        #         # --------------------------------------------

        #         if (
        #             not extracted
        #             and active_action.get("field_name")
        #             == "MULTI_FIELD_UPDATE"
        #         ):

        #             extracted = (
        #                 CreateService.extract_simple_field_value(
        #                     module=active_action["module"],
        #                     user_text=prompt,
        #                 )
        #                 or {}
        #             )

        #         # --------------------------------------------
        #         # Single-field fallback
        #         # --------------------------------------------

        #         if (
        #             not extracted
        #             and active_action.get("field_name")
        #             and active_action.get("field_name")
        #             != "MULTI_FIELD_UPDATE"
        #         ):

        #             extracted = {
        #                 active_action["field_name"]:
        #                 prompt.strip()
        #             }

        #     response = UpdateService.handle_update_workflow(
        #         session_id=session_id,
        #         user_input=prompt,
        #         active_action=active_action,
        #         client=crm_service.client,
        #         extracted_fields=extracted,
        #     )

        #     ChatRepository.save_chat_message(
        #         session_id=session_id,
        #         role="user",
        #         message=prompt,
        #     )

        #     assistant_message = (
        #         response.get("response")
        #         or response.get("summary")
        #         or ""
        #     ) if isinstance(response, dict) else str(response)

        #     ChatRepository.save_chat_message(
        #         session_id=session_id,
        #         role="assistant",
        #         message=assistant_message,
        #         response_json=json.dumps(response),
        #     )

        #     return {
        #         "success": True,
        #         "operation": response.get("operation"),
        #         "module": response.get("module"),
        #         "response": response,
        #         "records": response.get("records", []),
        #         "table": response.get("table"),
        #         "chart": response.get("chart"),
        #         "kpis": response.get("kpis"),

        #         # CHANGE THIS ALSO
        #         "summary": response.get("summary") or response.get("response"),

        #         "suggestions": response.get("suggestions", []),
        #         "pagination": response.get("pagination"),
        #         "query": {},
        #     }

        if state.get("pending_record_selection"):
            print("PENDING SELECTION MODE")
            print("USER INPUT =", prompt)

            user_input = prompt.strip().lower()

            selected = None

            if user_input.isdigit():

                selected = int(user_input)
                print("SELECTED =", selected)

            elif user_input.startswith("record "):

                value = user_input.replace("record", "").strip()

                if value.isdigit():
                    selected = int(value)

            elif user_input.startswith("show record"):

                value = user_input.replace("show record", "").strip()

                if value.isdigit():
                    selected = int(value)

            elif user_input == "first":
                selected = 1

            elif user_input == "second":
                selected = 2

            elif user_input == "third":
                selected = 3

            if selected:

                records = state["pending_records"]
                if not records:

                    state["pending_record_selection"] = None

                    return {
                        "success": False,
                        "operation": "search",
                        "module": state.get("current_module"),
                        "response": {
                            "summary": "The previous search is no longer available. Please search again.",
                            "kpis": None,
                            "table": None,
                            "chart": None,
                            "suggestions": [],
                        },
                        "records": [],
                        "table": None,
                        "chart": None,
                        "pagination": None,
                        "query": {},
                    }

                if 1 <= selected <= len(records):

                    record = records[selected - 1]

                    module = (
                        record.get("_module")
                        or record.get("module")
                        or state.get("current_module")
                    )

                    full_record = crm_service.client.get_record_by_id(
                        module,
                        record["id"]
                    )

                    state["selected_record"] = full_record
                    state["selected_record_data"] = full_record
                    state["selected_record_id"] = full_record["id"]

                    record = full_record

                    real_module = (
                        module                      # module used to fetch the record
                        or record.get("_module")
                        or record.get("module")
                    )

                    # Preserve the actual CRM module
                    record["_module"] = real_module

                    state["selected_record"] = record
                    state["selected_record_data"] = record
                    state["selected_record_id"] = record["id"]
                    state["selected_record_module"] = real_module

                    print("SELECTED RECORD =", record)

                    # IMPORTANT
                    state["current_module"] = real_module

                    state["pending_record_selection"] = None
                    state["pending_records"] = []

                    crm_result = {
                        "operation": "search",
                        "module": module,
                        "records": [record],
                        "table": None,
                        "chart": None,
                        "kpis": None,
                        "summary": None,
                        "suggestions": [],
                        "pagination": None,
                        "query": {},
                    }
                    summary = ResponseGeneration.generate_detail_view(
                        module=module,
                        record=record,
                    )

                    response = {
                        "summary": summary,
                        "table": None,
                        "chart": None,
                        "kpis": None,
                        "suggestions": [
                            f"Edit {module[:-1]}",
                            f"Delete {module[:-1]}",
                            f"Update {module[:-1]}"
                        ]
                    }
                    
                    # Save user selection
                    ChatRepository.save_chat_message(
                        session_id=session_id,
                        role="user",
                        message=prompt,
                    )

                    # Save assistant response
                    ChatRepository.save_chat_message(
                        session_id=session_id,
                        role="assistant",
                        message=response["summary"],
                        response_json=json.dumps(response),
                    )

                    return {
                        "success": True,
                        "detail_view": True,

                        "operation": crm_result["operation"],
                        "module": crm_result["module"],

                        "response": response,

                        "records": crm_result["records"],

                        "table": response.get("table"),
                        "chart": response.get("chart"),
                        "kpis": response.get("kpis"),

                        "summary": response.get("summary"),
                        "suggestions": response.get("suggestions", []),

                        "pagination": None,
                        "query": {},
                    }
                else:

                    return {
                        "success": False,
                        "operation": "search",
                        "module": state.get("current_module"),
                        "response": {
                            "summary": (
                                f"Please select a number between 1 and {len(records)}."
                            ),
                            "kpis": None,
                            "table": None,
                            "chart": None,
                            "suggestions": [],
                        },
                        "records": [],
                        "table": None,
                        "chart": None,
                        "pagination": None,
                        "query": {},
                    }
                    
        # --------------------------------------------------
        # Selected Record -> Start Update Workflow
        # --------------------------------------------------

        if state.get("selected_record"):

            lower_prompt = prompt.strip().lower()
            print("\n===== BEFORE ADD MORE =====")
            print(type(state.get("selected_record")))
            print(state.get("selected_record"))
            print("===========================\n")

            if lower_prompt in [
                "add more",
                "add more fields",
                "more fields",
                "show more",
                "show more fields",
                "remaining fields",
                "additional fields",
                "show additional fields",
            ]:

                # Always use the full record object.
                # selected_record may contain only the display name.
                record = (
                    state.get("selected_record_data")
                    or state.get("selected_record")
                )

                if not isinstance(record, dict):
                    return {
                        "success": False,
                        "operation": "update",
                        "module": state.get("current_module"),
                        "response": {
                            "summary": "No record is currently selected.",
                            "kpis": None,
                            "table": None,
                            "chart": None,
                            "suggestions": [],
                        },
                        "records": [],
                        "table": None,
                        "chart": None,
                        "kpis": None,
                        "summary": "No record is currently selected.",
                        "suggestions": [],
                        "pagination": None,
                        "query": {},
                    }

                # Determine the actual CRM module without refetching the record.
                real_module = (
                    record.get("_module")
                    or record.get("module")
                    or state.get("selected_record_module")
                    or state.get("current_module")
                )

                if not real_module:
                    return {
                        "success": False,
                        "operation": "update",
                        "response": {
                            "summary": "I could not determine the CRM module for this record.",
                            "kpis": None,
                            "table": None,
                            "chart": None,
                            "suggestions": [],
                        },
                        "records": [],
                        "table": None,
                        "chart": None,
                        "kpis": None,
                        "summary": "I could not determine the CRM module for this record.",
                        "suggestions": [],
                        "pagination": None,
                        "query": {},
                    }

                # Keep the selected-record state consistent.
                record["_module"] = real_module

                state["selected_record"] = record
                state["selected_record_data"] = record
                state["selected_record_id"] = record.get("id")
                state["selected_record_module"] = real_module
                state["current_module"] = real_module

                # Show only the optional fields that are still empty.
                summary = CreateService.build_optional_fields_prompt(
                    module=real_module,
                    collected_fields={},
                    current_record=record,
                )

                response = {
                    "summary": summary,
                    "kpis": None,
                    "table": None,
                    "chart": None,
                    "suggestions": [
                        "Continue",
                        "Cancel",
                    ],
                }

                # IMPORTANT:
                # Create the pending UPDATE workflow directly.
                # Do NOT call UpdateService.start_update() here.
                ActionRepository.create_pending_action(
                    session_id=session_id,
                    action_type="UPDATE",
                    module=real_module,
                    record_id=record["id"],
                    record_name=(
                        record.get("Full_Name")
                        or record.get("Name")
                        or record.get("Account_Name")
                        or record.get("Deal_Name")
                        or str(record.get("id"))
                    ),
                    field_name="MULTI_FIELD_UPDATE",
                    old_value="",
                    new_value=json.dumps({
                        "stage": "COLLECT_FIELDS",
                        "fields": {},
                    }),
                    status="AWAITING_DETAILS",
                )

                ChatRepository.save_chat_message(
                    session_id=session_id,
                    role="user",
                    message=prompt,
                )

                ChatRepository.save_chat_message(
                    session_id=session_id,
                    role="assistant",
                    message=response["summary"],
                    response_json=json.dumps(response),
                )

                return {
                    "success": True,
                    "operation": "update",
                    "module": real_module,
                    "response": response,
                    "records": [],
                    "table": None,
                    "chart": None,
                    "kpis": None,
                    "summary": response["summary"],
                    "suggestions": response["suggestions"],
                    "pagination": None,
                    "query": {},
                }
        # --------------------------------------------------
        # Contextual Update
        # --------------------------------------------------
        print("=" * 60)
        print("CHECKING CONTEXTUAL UPDATE")
        print("selected_record =", state.get("selected_record"))
        print("operation =", understanding.get("operation"))
        print("=" * 60)

        if (
            understanding["operation"] == "update"
            and state.get("selected_record")
        ):

            update = understanding["update"]

            # --------------------------------------------------
            # IMPORTANT:
            # selected_record may contain only the display name
            # such as "Rahul Sharma".
            #
            # selected_record_data contains the actual CRM record.
            # Use the full record for update operations.
            # --------------------------------------------------

            selected_record_data = (
                state.get("selected_record_data")
                if isinstance(state.get("selected_record_data"), dict)
                else None
            )

            selected_record = selected_record_data

            # Safety fallback:
            # If selected_record_data is unavailable, only use
            # selected_record when it is already a dictionary.
            if selected_record is None and isinstance(
                state.get("selected_record"),
                dict
            ):
                selected_record = state.get("selected_record")

            if not selected_record:
                return {
                    "success": False,
                    "operation": "update",
                    "module": state.get("current_module"),
                    "response": {
                        "summary": "The selected record details are no longer available. Please select the record again.",
                        "kpis": None,
                        "table": None,
                        "chart": None,
                        "suggestions": [],
                    },
                    "records": [],
                    "table": None,
                    "chart": None,
                    "kpis": None,
                    "summary": "The selected record details are no longer available. Please select the record again.",
                    "suggestions": [],
                    "pagination": None,
                    "query": {},
                }

            extracted_fields = {}

            try:

                extracted_fields = await CreateFieldExtractor.extract_fields(
                    module=(
                        selected_record.get("_module")
                        or selected_record.get("module")
                        or state.get("selected_record_module")
                        or state.get("current_module")
                    ),
                    user_text=prompt,
                    api_keys=api_keys,
                ) or {}

            except Exception as e:

                print("Update Field Extraction Error:", e)

            print("\n===== UPDATE LLM FIELDS =====")
            print(extracted_fields)
            print("=============================\n")

            result = UpdateService.start_update(
                session_id=session_id,
                target_record=None,
                raw_field=update.get("field_name"),
                new_value=update.get("new_value"),
                extracted_fields=extracted_fields,
                client=crm_service.client,
                user_query=prompt,
                selected_record=selected_record,
            )

            ChatRepository.save_chat_message(
                session_id=session_id,
                role="user",
                message=prompt,
            )

            assistant_message = (
                result.get("response", "")
                if isinstance(result, dict)
                else str(result)
            )

            ChatRepository.save_chat_message(
                session_id=session_id,
                role="assistant",
                message=assistant_message,
                response_json=json.dumps(result),
            )

            return {
                "success": True,
                "operation": result.get("operation"),
                "module": result.get("module"),
                "response": result,
                "records": result.get("records", []),
                "table": result.get("table"),
                "chart": result.get("chart"),
                "kpis": result.get("kpis"),
                "summary": result.get("response"),
                "suggestions": result.get("suggestions", []),
                "pagination": result.get("pagination"),
                "query": {},
            }
        
        # -----------------------------
        # Navigation Queries (Cache)
        # -----------------------------

        crm_result = await read_service.execute(
            query=prompt,
            session_id=session_id,
            api_keys=api_keys,
            current_module=state.get("current_module"),
        )

        if crm_result.get("module"):
            state["current_module"] = crm_result["module"]
        
        print("\n===== CRM RESULT =====")
        print(crm_result)
        print("======================\n")

        # --------------------------------------------------
        # CREATE WORKFLOW
        # --------------------------------------------------

        if crm_result.get("workflow") == "CREATE":

            # Detect whether the original prompt already contains details.
            understanding = QueryUnderstanding.understand_query(
                prompt,
                current_module=state.get("current_module")
            )

            raw_text = (
                understanding.get("create", {})
                .get("raw_text", "")
            )

            # If the user typed only "Create a lead"
            # don't extract yet.
            if raw_text.strip().lower() in [
                "create a lead",
                "create lead",
                "create contact",
                "create account",
                "create deal",
                "",
            ]:

                response = {
                    "summary": crm_result.get("message"),
                    "kpis": None,
                    "table": None,
                    "chart": None,
                    "suggestions": [],
                }

            else:

                active_action = ActionRepository.get_active_pending_action(session_id)

                extracted = await CreateService.extract_fields(
                    crm_result["module"],
                    prompt,
                    api_keys,
                )

                print("\n===== FIRST MESSAGE EXTRACTION =====")
                print(extracted)
                print("====================================\n")

                if extracted:

                    response = CreateWorkflowService.process_initial_create(
                        active_action,
                        extracted,
                    )

                else:

                    response = {
                        "summary": crm_result.get("message"),
                        "kpis": None,
                        "table": None,
                        "chart": None,
                        "suggestions": [],
                    }

            ChatRepository.save_chat_message(
                session_id=session_id,
                role="user",
                message=prompt,
            )

            ChatRepository.save_chat_message(
                session_id=session_id,
                role="assistant",
                message=response["summary"],
                response_json=json.dumps(response),
            )

            return {
                "success": True,
                "operation": "create",
                "module": crm_result.get("module"),
                "response": response,
                "records": [],
                "table": None,
                "chart": None,
                "kpis": None,
                "summary": response["summary"],
                "suggestions": [],
                "pagination": None,
                "query": {},
            }
            
        response = await response_service.generate_response(
            query=prompt,
            crm_result=crm_result,
            history=history,
            session_id=session_id,
            api_keys=api_keys,
        )
        print(response)
        
        # Save user message
        ChatRepository.save_chat_message(
            session_id=session_id,
            role="user",
            message=prompt,
        )

        # Save assistant message
        assistant_message = response

        if isinstance(response, dict):
            assistant_message = response.get("summary", "")

        ChatRepository.save_chat_message(
            session_id=session_id,
            role="assistant",
            message=assistant_message,
            response_json=json.dumps(response),
        )

        return {
            "success": True,

            "operation": crm_result.get("operation"),
            "module": crm_result.get("module"),

            "response": response,

            "records": crm_result.get("records", []),

            "table": crm_result.get("table"),

            "chart": crm_result.get("chart"),

            "kpis": crm_result.get("kpis"),

            "summary": response.get("summary") if isinstance(response, dict) else crm_result.get("summary"),

            "suggestions": response.get("suggestions", []) if isinstance(response, dict) else crm_result.get("suggestions", []),

            "pagination": crm_result.get("pagination"),

            "query": crm_result.get("query"),
        }