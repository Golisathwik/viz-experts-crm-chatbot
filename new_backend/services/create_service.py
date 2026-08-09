from typing import Dict, Any
import json
from new_backend.repositories.action_repository import ActionRepository
from new_backend.services.field_validation_service import FieldValidationService
from new_backend.ai.create_field_extractor import CreateFieldExtractor
from new_backend.ai.response_generation import ResponseGeneration
class CreateService:

    @staticmethod
    def start_create(
        session_id: int,
        create_data: Dict[str, Any],
        client,
        user_query: str,
    ):

        module = create_data.get("module")

        if not module:

            return {
                "success": False,
                "message": "I couldn't determine which CRM module you want to create."
            }

        # Create pending workflow
        ActionRepository.create_pending_action(
            session_id=session_id,
            action_type="CREATE",
            module=module,
            record_id="CREATE",
            record_name="NEW_RECORD",
            field_name="CREATE_FIELDS",
            old_value=create_data.get("raw_text", user_query),
            new_value=json.dumps({
                "stage": "REQUIRED_FIELDS",
                "fields": {}
            }),
        )

        return {
            "success": True,
            "workflow": "CREATE",
            "status": "STARTED",
            "module": module,
            "message": (
                f"Creating a new {module[:-1]}.\n\n"
                "I'll extract the information you provide and then check for any required fields before creating the record."
            ),
        }

    
    @staticmethod
    def build_optional_fields_prompt(
        module: str,
        collected_fields: dict,
        current_record: dict = None,
    ):
        print("Collected:", collected_fields)
        print("Current Record:", current_record)

        for field in FieldValidationService.get_optional_fields(module):

            value = current_record.get(field) if current_record else None

            print(field, "=", value)

        remaining = []

        labels = FieldValidationService.get_field_labels()

        for field in FieldValidationService.get_optional_fields(module):

            if field in collected_fields:
                continue

            if current_record:

                value = current_record.get(field)

                # Support display labels from detail view
                if value is None:
                    label = labels.get(field)
                    if label:
                        value = current_record.get(label)

                # Support spaces instead of underscores
                if value is None:
                    value = current_record.get(field.replace("_", " "))

                if isinstance(value, dict):
                    value = value.get("name") or value.get("id")

                if value not in [None, "", [], {}]:
                    continue

            remaining.append(field)

        if not remaining:

            return (
                "All optional fields for this record already have values.\n\n"
                "Reply:\n"
                "• Continue\n"
                "• Cancel"
            )

        labels = FieldValidationService.get_field_labels()

        lines = [
            "You can still provide any of these optional fields:",
            "",
        ]

        for field in remaining:
            lines.append(f"• {labels.get(field, field.replace('_', ' '))}")

        lines.extend([
            "",
            "You may enter one or multiple fields together.",
            "",
            "Type 'Continue' when finished.",
        ])

        return "\n".join(lines)
    
    @staticmethod
    def build_record_optional_fields_prompt(
        module: str,
        record: dict,
    ):

        remaining = FieldValidationService.get_remaining_optional_fields(
            module,
            record,
        )

        labels = FieldValidationService.get_field_labels()

        if not remaining:
            return (
                "✅ All available fields already have values."
            )

        lines = [
            "You can also update these remaining fields:",
            "",
        ]

        for field in remaining:

            lines.append(
                f"• {labels.get(field, field.replace('_', ' '))}"
            )

        lines.extend([
            "",
            "You can enter one or multiple fields together.",
            "",
            "Examples:",
            "• Phone 9876543210",
            "• Email john@gmail.com",
            "• Website www.abc.com",
            "• Industry Software",
            "",
            "Type Continue when finished.",
        ])

        return "\n".join(lines)
    
    
    @staticmethod
    def build_preview(
        module: str,
        fields: dict,
    ):

        FIELD_LABELS = FieldValidationService.get_field_labels()


        lines = []

        lines.append("✅ Required information collected.\n")
        lines.append("Current Record Preview:\n")

        for field in FieldValidationService.get_display_order(module):

            if field not in fields:
                continue

            value = fields[field]

            if value in [None, ""]:
                continue

            label = FIELD_LABELS.get(field, field.replace("_", " "))

            lines.append(f"• {label}: {value}")

        lines.append("")
        lines.append(
            "Would you like to add optional fields before creating this record?"
        )
        lines.append("")
        lines.append("Reply:")
        lines.append("• Continue")
        lines.append("• Add more")
        lines.append("• Cancel")

        return "\n".join(lines)  
    
    @staticmethod
    def build_update_preview(
        module: str,
        record: dict,
        updated_fields: dict,
    ):

        FIELD_LABELS = FieldValidationService.get_field_labels()

        display_order = FieldValidationService.get_display_order(module)

        lines = []

        record_name = (
            record.get("Full_Name")
            or record.get("Deal_Name")
            or record.get("Account_Name")
            or record.get("Name")
            or "Selected Record"
        )

        module_name = module[:-1] if module.endswith("s") else module

        lines.append("## UPDATE PREVIEW")
        lines.append("")

        lines.append(f"**Record:** {module_name} : {record_name}")
        lines.append("")

        lines.append("### Current Record")
        lines.append("")

        for field in display_order:

            if field in updated_fields:
                continue

            value = record.get(field)

            if isinstance(value, dict):
                value = value.get("name") or value.get("id")

            if value in [None, "", [], {}]:
                continue

            label = FIELD_LABELS.get(field, field.replace("_", " "))

            lines.append(f"• **{label}:** {value}")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("### Changes")
        lines.append("")

        for field in display_order:

            if field not in updated_fields:
                continue

            label = FIELD_LABELS.get(field, field.replace("_", " "))

            old = record.get(field)

            if isinstance(old, dict):
                old = old.get("name") or old.get("id")

            if old in [None]:
                old = "Not Set"

            new = updated_fields[field]

            lines.append(f"**{label}**")
            lines.append(f"• Before: {old}")
            lines.append(f"• After : {new}")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("Reply:")
        lines.append("")
        lines.append("• Confirm")
        lines.append("• Add More")
        lines.append("• Cancel")

        return "\n".join(lines) 

    @staticmethod
    def build_success_summary(
        module,
        fields,
        verification_passed=True,
    ):

        labels = FieldValidationService.get_field_labels()

        module_singular = module[:-1] if module.endswith("s") else module
        module_plural = module.lower()

        lines = [
            f"✅ {module_singular} updated successfully.",
            "",
        ]

        for field, value in fields.items():

            label = labels.get(
                field,
                field.replace("_", " "),
            )

            lines.append(f"• {label}: {value}")

        lines.extend([
            "",
            f"Verification: {'Passed' if verification_passed else 'Confirmed (Pending Sync)'}",
            "",
            "Cache: Updated",
            "",
            "**Follow-up Suggestions**:",
            "- **show updated record**",
            f"- **show all {module_plural}**",
            "- **update another field**",
            "- **show analytics**",
            "- **show dashboard**",
        ])

        return "\n".join(lines)

    @staticmethod
    def build_missing_fields_response(
        module: str,
        extracted_fields: dict,
    ):
        """
        Validate mandatory fields and build a professional response.
        """

        result = FieldValidationService.validate_required_fields(
            module,
            extracted_fields,
        )

        FIELD_LABELS = FieldValidationService.get_field_labels()

        DISPLAY_ORDER = [
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
        ]

        # -----------------------------------
        # All mandatory fields collected
        # -----------------------------------

        if result["complete"]:

            return {
                "complete": True,
                "summary": None,
            }

        # -----------------------------------
        # Build response
        # -----------------------------------

        lines = []

        lines.append("## Summary")
        lines.append("")

        # -------------------------
        # Collected Information
        # -------------------------

        if extracted_fields:

            lines.append("### ✅ Information Collected")
            lines.append("")

            for field in DISPLAY_ORDER:

                if field not in extracted_fields:
                    continue

                value = extracted_fields[field]

                if value in [None, ""]:
                    continue

                label = FIELD_LABELS.get(
                    field,
                    field.replace("_", " "),
                )

                lines.append(f"• **{label}:** {value}")

            lines.append("")

        # -------------------------
        # Missing Mandatory
        # -------------------------

        lines.append("### ❗ Mandatory Fields Still Required")
        lines.append("")

        for field in result["missing"]:

            label = FIELD_LABELS.get(
                field,
                field.replace("_", " "),
            )

            lines.append(f"• **{label}**")

        lines.append("")
        lines.append(
            "Please provide the above mandatory field(s) to continue."
        )

        return {
            "complete": False,
            "missing": result["missing"],
            "summary": "\n".join(lines),
        }
        
    @staticmethod
    def update_preview_fields(
        active_action,
        extracted,
    ):

        workflow_state = json.loads(
            active_action.get("new_value") or "{}"
        )

        fields = workflow_state.get("fields", {})

        for key, value in extracted.items():

            if value is None:
                fields[key] = ""
                continue

            if isinstance(value, str) and not value.strip():
                continue

            valid, message, normalized = (
                FieldValidationService.validate_field_value(
                    key,
                    value,
                )
            )

            if not valid:
                return {
                    "success": False,
                    "summary": message,
                }

            fields[key] = normalized

        workflow_state["fields"] = fields

        ActionRepository.update_pending_action(
            action_id=active_action["id"],
            new_value=json.dumps(workflow_state),
        )

        return {
            "success": True,
            "fields": fields,
        }
        
    @staticmethod
    def process_collected_fields(
        active_action,
        extracted,
    ):

        state = {
            "stage": "REQUIRED_FIELDS",
            "fields": {},
        }

        try:
            state = json.loads(
                active_action.get("new_value") or "{}"
            )
        except Exception:
            pass

        fields = state.get("fields", {})

        for key, value in extracted.items():

            if value is None:
                continue

            if isinstance(value, str) and not value.strip():
                continue

            valid, message, normalized = (
                FieldValidationService.validate_field_value(
                    key,
                    value,
                )
            )

            if not valid:

                return {
                    "success": False,
                    "summary": message,
                }

            fields[key] = normalized

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

        return {
            "success": True,
            "fields": fields,
            "complete": validation["complete"],
        }
        
    @staticmethod
    async def extract_fields(
        module,
        prompt,
        api_keys,
    ):

        extracted = await CreateFieldExtractor.extract_fields(
            module=module,
            user_text=prompt,
            api_keys=api_keys,
        )

        return extracted or {}
        
    @staticmethod
    def confirm_create(
        active_action,
        crm_service,
    ):

        workflow_state = json.loads(active_action["new_value"])

        fields = workflow_state.get("fields", {})

        crm_result = crm_service.create_record(
            module=active_action["module"],
            fields=fields,
        )

        if crm_result.get("success"):

            ActionRepository.update_pending_action(
                action_id=active_action["id"],
                status="COMPLETED",
            )

            record = crm_result.get("created_record", {})

            summary = ResponseGeneration.generate_detail_view(
                module=active_action["module"],
                record=record,
            )

            response = {
                "summary": (
                    "✅ Record created successfully.\n\n"
                    + summary
                ),
                "kpis": None,
                "table": None,
                "chart": None,
                "suggestions": [],
            }

        else:

            response = {
                "summary": crm_result.get(
                    "error",
                    "Failed to create record.",
                ),
                "kpis": None,
                "table": None,
                "chart": None,
                "suggestions": [],
            }

        return response
    

    @staticmethod
    def handle_create_workflow(
        session_id: int,
        user_input: str,
        active_action,
        client,
    ):

        clean = user_input.strip().lower()

        if clean in [
            "cancel",
            "cancel it",
            "cancel create",
            "stop",
            "abort",
            "never mind",
            "forget it",
            "exit",
            "quit",
        ]:

            ActionRepository.update_pending_action(
                active_action["id"],
                status="FAILED",
            )

            return {
                "success": True,
                "workflow": "CREATE",
                "status": "CANCELLED",
                "module": active_action["module"],
                "message": (
                    "✅ Create operation cancelled.\n\n"
                    "No record has been created."
                ),
            }

        return {
            "success": True,
            "workflow": "CREATE",
            "status": "WAITING_FOR_DETAILS",
            "module": active_action["module"],
            "message": "Please provide the record details.",
        }