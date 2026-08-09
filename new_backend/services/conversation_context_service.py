"""
conversation_context_service.py

Conversation context manager for V2 architecture.

Responsibilities:
- Clean conversation history
- Follow-up detection
- Active record context injection
- Routing validation

Does NOT:
- Call CRM
- Call LLM
- Build prompts
"""

import json
import re
from typing import Dict, Any, List, Optional

from new_backend.services.cache_service import CacheService


class ConversationContextService:

    @staticmethod
    def clean_history(
        history: List[Dict[str, str]],
        count: int,
        session_id: Optional[int] = None,
    ) -> List[Dict]:

        cleaned = []

        active_context = None

        if session_id:

            state = CacheService.get_state(session_id)

            if (
                state.get("selected_record")
                and ConversationContextService.is_query_context_relevant(
                    history[-1]["message"] if history else ""
                )
            ):
                active_context = (
                    f"Current CRM Record:\n"
                    f"Module : {state['current_module']}\n"
                    f"Name   : {state['selected_record']}\n"
                    f"ID     : {state['selected_record_id']}"
                )

        for msg in history[-count:]:

            role = msg["role"]
            content = msg["message"]

            if role == "assistant":

                content = ConversationContextService._compress_response(content)

            cleaned.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        if active_context:

            cleaned.insert(
                -1,
                {
                    "role": "system",
                    "content": active_context,
                },
            )

        return cleaned

    @staticmethod
    def _compress_response(content: str) -> str:

        try:

            data = json.loads(content)

            minimized = {
                "intent": data.get("intent_detected"),
                "response": data.get("text_response"),
                "visualizations": [],
            }

            for viz in data.get("visualizations", []):

                minimized["visualizations"].append(
                    {
                        "type": viz.get("visualization_type"),
                        "title": viz.get("chart_metadata", {}).get("title"),
                    }
                )

            return json.dumps(minimized)

        except Exception:

            content = re.sub(
                r"\*\(Rate limit hit.*?\)\*",
                "",
                content,
                flags=re.DOTALL,
            )

            return content[:400]

    @staticmethod
    def is_query_context_relevant(query: str) -> bool:

        q = query.lower()

        ignore = [
            "show all",
            "list all",
            "display all",
            "dashboard",
            "statistics",
            "hello",
            "hi",
            "hey",
            "what is zoho",
            "who are you",
        ]

        return not any(x in q for x in ignore)

    @staticmethod
    def validate_routing(
        intent_data: Dict[str, Any],
        query: str,
        active_record_exists: bool,
    ) -> Dict[str, Any]:

        q = query.lower()

        if any(
            x in q
            for x in [
                "dashboard",
                "statistics",
                "summary",
                "analytics",
            ]
        ):
            intent_data["category"] = "analytics"

        if (
            active_record_exists
            and len(q.split()) <= 8
        ):
            followup = [
                "phone",
                "email",
                "owner",
                "company",
                "website",
                "industry",
                "revenue",
                "stage",
                "status",
            ]

            if any(f in q for f in followup):

                intent_data["follow_up"] = True

        return intent_data