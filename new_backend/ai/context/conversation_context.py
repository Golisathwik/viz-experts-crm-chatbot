"""
conversation_context.py

Handles all conversation-related context for the chatbot.

Responsibilities:
- Active Record Context
- Conversation History Cleanup
- Follow-up Detection
- Context Relevance
- Routing Validation

NOTE:
This file should NOT:
- Call Zoho CRM
- Call any LLM
- Build prompts
- Stream responses
"""

import json
import re
from typing import Dict, Any, List, Optional
from new_backend.repositories.chat_repository import ChatRepository


class ConversationContext:
    """
    Central manager for conversation context.
    """

    @staticmethod
    def clean_history(history: List[Dict[str, str]], count: int, session_id: Optional[int] = None) -> List[Dict[str, str]]:
        cleaned = []
        
        # Priority 2: Fetch current active record description if session_id is provided
        active_record_desc = None
        if session_id:
            latest_query = history[-1]["message"] if history else ""
            if ConversationContext.is_query_context_relevant(latest_query):
                try:
                    active_ctx = ChatRepository.get_active_context(session_id)
                    active_module = active_ctx.get("active_module")
                    active_id = active_ctx.get("active_record_id")
                    active_name = active_ctx.get("active_record_name")
                    if active_module and active_id and active_name:
                        active_record_desc = f"Currently active/selected Zoho CRM record: {active_module[:-1] if active_module.endswith('s') else active_module} '{active_name}' (ID: {active_id})."
                except Exception:
                    pass

        for msg in history[-count:]:
            role = msg["role"]
            content = msg["message"]
            if role == "assistant":
                try:
                    trimmed = content.strip()
                    if "*(Rate limit hit. Waiting" in trimmed:
                        first_brace = trimmed.find("{")
                        if first_brace != -1:
                            trimmed = trimmed[first_brace:]
                    
                    parsed = None
                    if trimmed.startswith("{") and trimmed.endswith("}"):
                        try:
                            parsed = json.loads(trimmed)
                            if isinstance(parsed, dict) and "text_response" in parsed:
                                inner_text = parsed["text_response"].strip()
                                if inner_text.startswith("{") and inner_text.endswith("}"):
                                    try:
                                        parsed = json.loads(inner_text)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                    
                    if parsed is None:
                        cleaned_msg = re.sub(r"\*\(Rate limit hit\. Waiting.*?\)\*", "", trimmed).strip()
                        intent_match = re.search(r"\bIntent:\s*(.*?)(?:\n|$)", cleaned_msg, re.IGNORECASE)
                        response_match = re.search(r"\bResponse:\s*([\s\S]*?)(?:\bVisualizations:|$)", cleaned_msg, re.IGNORECASE)
                        
                        intent = ""
                        response = cleaned_msg
                        
                        if intent_match and response_match:
                            intent = intent_match.group(1).strip()
                            response = response_match.group(1).strip()
                        elif response_match:
                            response = response_match.group(1).strip()
                        elif intent_match:
                            intent = intent_match.group(1).strip()
                            response = cleaned_msg.replace(intent_match.group(0), "").strip()
                        
                        response = re.sub(r"^(?:Intent|Response|Visualizations):\s*", "", response, flags=re.IGNORECASE).strip()
                        
                        parsed = {
                            "intent_detected": intent or "general_chat",
                            "text_response": response,
                            "visualizations": []
                        }
                    
                    minimized = {
                        "intent_detected": parsed.get("intent_detected", ""),
                        "text_response": parsed.get("text_response", ""),
                        "visualizations": []
                    }
                    for v in parsed.get("visualizations", []):
                        v_type = v.get("visualization_type", "")
                        v_title = v.get("chart_metadata", {}).get("title", "")
                        v_cols = v.get("columns")
                        v_data = v.get("data", [])
                        
                        if v_type == "table":
                            minimized["visualizations"].append({
                                "visualization_type": v_type,
                                "chart_metadata": {"title": v_title},
                                "columns": v_cols,
                                "data": v_data[:2]
                            })
                        else:
                            minimized["visualizations"].append({
                                "visualization_type": v_type,
                                "chart_metadata": {"title": v_title},
                                "data": v_data
                            })
                    content = json.dumps(minimized)
                except Exception:
                    fallback_text = content[:300]
                    fallback_text = re.sub(r"\*\(Rate limit hit\. Waiting.*?\)\*", "", fallback_text).strip()
                    content = json.dumps({
                        "intent_detected": "general_chat",
                        "text_response": fallback_text,
                        "visualizations": []
                    })
            cleaned.append({"role": role, "content": content})
            
        # Priority 2 context injection: insert active record context right before the last user message
        if active_record_desc and len(cleaned) >= 1:
            cleaned.insert(-1, {"role": "system", "content": active_record_desc})
        elif active_record_desc:
            cleaned.append({"role": "system", "content": active_record_desc})
            
        return cleaned

    @staticmethod
    def is_query_context_relevant(query: str) -> bool:
        """Determine if the current query should ignore previous CRM active context."""
        q_lower = query.lower().strip()
        
        # Greetings, general knowledge, generic Zoho CRM chitchat
        if any(w in q_lower for w in ["what is zoho crm", "what is zoho", "who are you", "how are you", "hello", "hi", "hey", "good morning", "good afternoon"]):
            return False
            
        # Explicit new listing or dashboards
        if any(w in q_lower for w in ["show all", "list all", "display all", "get all", "give me all", "show leads", "show deals", "show contacts", "show accounts", "show opportunities", "show activities", "show dashboard", "pipeline summary"]):
            return False
            
        return True

    @staticmethod
    def validate_and_sanitize_routing(intent_data: Dict[str, Any], query: str, active_record_exists: bool) -> Dict[str, Any]:
        """Validate and sanitize the intent routing to prevent conflicts and guarantee exactly one route."""
        q_lower = query.lower().strip()
        intent = intent_data.get("intent", "general_chat")
        category = intent_data.get("category", "")
        query_term = intent_data.get("query_term", None)
        
        # 1. Override for General Knowledge / Greetings
        if any(phrase in q_lower for phrase in ["what is zoho crm", "what is zoho", "who are you", "how are you"]) or any(word in q_lower.split() for word in ["hello", "hi", "hey"]):
            return {"category": "Zoho CRM Knowledge", "intent": "general_chat", "query_term": None}
            
        # 2. Override for Update workflows
        if any(w in q_lower for w in ["change", "update", "modify", "correct", "set"]) and any(w in q_lower for w in ["phone", "email", "mobile", "stage", "status", "amount", "value", "closing date", "date", "website", "revenue", "company", "industry", "employees"]):
            return {"category": "CRM Update", "intent": "crm_update", "query_term": query_term}
            
        # 3. Override for Dashboard / Analytics
        if any(w in q_lower for w in ["dashboard", "statistics", "crm stats", "stats"]):
            return {"category": "CRM Analytics", "intent": "crm_stats", "query_term": None}
            
        # 4. Override for Listing triggers
        if "leads" in q_lower and any(w in q_lower for w in ["show all", "list all", "display", "get all", "give me all"]):
            return {"category": "CRM Search", "intent": "show_leads", "query_term": None}
        if "deals" in q_lower and any(w in q_lower for w in ["show all", "list all", "display", "get all", "give me all"]):
            return {"category": "CRM Search", "intent": "show_deals", "query_term": None}
        if "contacts" in q_lower and any(w in q_lower for w in ["show all", "list all", "display", "get all", "give me all"]):
            return {"category": "CRM Search", "intent": "show_contacts", "query_term": None}
        if "accounts" in q_lower and any(w in q_lower for w in ["show all", "list all", "display", "get all", "give me all"]):
            return {"category": "CRM Search", "intent": "show_accounts", "query_term": None}
        if "companies" in q_lower and any(w in q_lower for w in ["show all", "list all", "display", "get all", "give me all"]):
            return {"category": "CRM Search", "intent": "show_accounts", "query_term": None}
            
        # 5. Active record follow-ups
        if active_record_exists:
            follow_up_keywords = ["phone", "email", "contact", "owner", "owned", "revenue", "website", "url", "address", "company", "industry", "employee", "employees", "stage", "amount", "value", "status"]
            if any(w in q_lower for w in follow_up_keywords) and len(q_lower.split()) <= 10:
                return {"category": "Follow-up Conversation", "intent": "search_lead", "query_term": None}

        return intent_data

    @staticmethod
    def inject_active_record_context(messages, active_record):
        """
        Injects active record context into the conversation.
        """
        raise NotImplementedError()