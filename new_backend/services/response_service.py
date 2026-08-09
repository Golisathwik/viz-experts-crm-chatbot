from datetime import datetime
from typing import Dict, Any, List

from new_backend.ai.prompts.prompt_builder import PromptBuilder
from new_backend.ai.context.conversation_context import ConversationContext
from new_backend.ai.llm.router import get_ai_router
from new_backend.services.crm_context_service import CRMContextService


class ResponseService:

    def __init__(self):
        self.router = get_ai_router()

    async def generate_response(
        self,
        query: str,
        crm_result: Dict[str, Any],
        history: List[Dict[str, Any]],
        session_id: int,
        api_keys: Dict[str, str],
    ):

        history = ConversationContext.clean_history(
            history,
            count=5,
            session_id=session_id,
        )

        current_date = datetime.now().strftime("%d %B %Y")

        operation = crm_result.get("operation")

        records = crm_result.get("records", [])
        records = CRMContextService.optimize_records(records)

        module = crm_result.get("module", "")
        table = crm_result.get("table")
        chart = crm_result.get("chart")
        kpis = crm_result.get("kpis")
    
        # Operations that should NOT go to the LLM.
        # ReadService already generated the final response.
        # Operations that should NOT go to the LLM.
        # These responses are already fully prepared by the backend.

        if operation in {
            "search",
            "show",
            "filter",
            "sort",
            "update",
            "delete",
            "analytics",
            "navigation",
            "record",
        }:

            if crm_result.get("response"):
                return crm_result["response"]

            # Analytics response is already built by the backend.
            if operation == "analytics":

                return {
                    "summary": crm_result.get("summary"),
                    "kpis": crm_result.get("kpis"),
                    "table": crm_result.get("table"),
                    "chart": crm_result.get("chart"),
                    "suggestions": crm_result.get("suggestions", []),
                }

        if operation in {
            "show",
            "search",
            "sort",
            "filter",
            "analytics",
            "navigation",
            "record",
        }:

            pagination = crm_result.get("pagination")

            total_records = (
                pagination.get("total")
                if pagination
                else kpis.get("record_count")
                if kpis
                else len(records)
            )

            context = {
                "module": module,
                "record_count": total_records,
                "current_page_records": len(records),
                "pagination": pagination,
                "kpis": kpis,
                "chart": chart,
                "table_columns": (
                    table.get("columns", [])
                    if table
                    else []
                ),
            }

            system_prompt = (
                PromptBuilder.build_reasoning_prompt(current_date)
                + "\n\n"
                + "CRM Analytics Context:\n"
                + str(context)
            )

        else:

            system_prompt = PromptBuilder.build_general_chat_prompt(
                current_date
            )

        response = await self.router.generate_response(
            prompt=query,
            system_prompt=system_prompt,
            messages=history,
            api_keys=api_keys,
        )

        return response