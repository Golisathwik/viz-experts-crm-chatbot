import json

from new_backend.repositories.action_repository import ActionRepository
from new_backend.services.field_validation_service import FieldValidationService
from new_backend.services.create_service import CreateService

class CreateWorkflowService:

    @staticmethod
    def process_initial_create(
        active_action,
        extracted,
    ):
        if extracted:
        
            # Load previously extracted fields
            state = {
                "stage": "REQUIRED_FIELDS",
                "fields": {},
            }

            try:
                state = json.loads(
                    active_action.get("new_value") or "{}"
                )
            except:
                pass

            fields = state.get("fields", {})

            for key, value in extracted.items():

                if value is None:
                    continue

                if isinstance(value, str) and not value.strip():
                    continue

                valid, message, normalized = FieldValidationService.validate_field_value(
                    key,
                    value,
                )

                if not valid:

                    response = {
                        "summary": message,
                        "kpis": None,
                        "table": None,
                        "chart": None,
                        "suggestions": [],
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
                        "suggestions": [],
                        "pagination": None,
                        "query": {},
                    }

                fields[key] = normalized
                
            print("\n===== MERGED FIELDS =====")
            print(fields)
            print("=========================\n")

            state["fields"] = fields
            validation = FieldValidationService.validate_required_fields(
                active_action["module"],
                fields,
            )

            if validation["complete"]:
                state["stage"] = "PREVIEW"
            else:
                state["stage"] = "REQUIRED_FIELDS"

            ActionRepository.update_pending_action(
                action_id=active_action["id"],
                new_value=json.dumps(state),
            )
            active_action = ActionRepository.get_active_pending_action(
                active_action["session_id"]
            )

            print("\n===== DATABASE STATE =====")
            print(active_action["new_value"])
            print("==========================\n")

            extracted = fields

            validation = CreateService.build_missing_fields_response(
                active_action["module"],
                extracted,
            )

            if not validation["complete"]:

                response = {
                    "summary": validation["summary"],
                    "kpis": None,
                    "table": None,
                    "chart": None,
                    "suggestions": [],
                }

            else:

                summary = CreateService.build_preview(
                    active_action["module"],
                    extracted,
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

        else:

            response = {
                "summary": "Please provide the record details.",
                "kpis": None,
                "table": None,
                "chart": None,
                "suggestions": [],
            }
            
        return response