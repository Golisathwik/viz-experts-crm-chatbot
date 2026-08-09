import re
from typing import Optional, Dict, Any
from new_backend.ai.delete_detector import DeleteDetector
from new_backend.ai.module_detector import ModuleDetector
from new_backend.ai.sort_detector import SortDetector
from new_backend.ai.update_detector import UpdateDetector
from new_backend.ai.create_detector import CreateDetector
from new_backend.ai.search_detector import SearchDetector
from new_backend.ai.query_utils import QueryUtils

INTENT_PATTERNS = {
    "show_leads": [
        r"\bshow\b.*\bleads\b",
        r"\blist\b.*\bleads\b",
        r"\bget\b.*\bleads\b",
        r"\ball leads\b",
    ],
    "show_contacts": [
        r"\bshow\b.*\bcontacts\b",
        r"\blist\b.*\bcontacts\b",
        r"\ball contacts\b",
    ],
    "show_accounts": [
        r"\bshow\b.*\baccounts\b",
        r"\blist\b.*\baccounts\b",
        r"\bget\b.*\baccounts\b",
        r"\ball accounts\b",
    ],
    "show_deals": [
        r"\bshow\b.*\bdeals\b",
        r"\blist\b.*\bdeals\b",
        r"\ball deals\b",
        r"\bopen deals\b",
    ],
    "show_activities": [
        r"\bactivities\b",
        r"\btasks\b",
        r"\bcalls\b",
        r"\bmeetings\b",
    ],
    "pipeline_summary": [
        r"\bpipeline\b",
        r"\bsales pipeline\b",
    ],
    "crm_stats": [
        r"\bcrm stats\b",
        r"\bstatistics\b",
    ]
}


class IntentDetector:

    @staticmethod
    def detect_intent(query: str) -> Optional[Dict[str, Any]]:

        q = QueryUtils.normalize_query(query)

        module = ModuleDetector.detect_module(q)

        update = UpdateDetector.extract_update_details_deterministic(q)

        if update:
            return {
                "intent": "update_record",
                "module": module,
                "update_data": update,
            }
        
        delete = DeleteDetector.extract_delete_details(q)

        if delete:
            return {
                "intent": "delete_record",
                "module": module,
                "delete_data": delete,
            }
            
        create = CreateDetector.extract_create_details(q)

        if create:
            return {
                "intent": "create_record",
                "module": module,
                "create_data": create,
            }

        sort = SortDetector.detect_sort(q)

        if sort and module:

            return {
                "intent": f"show_{module.lower()}",
                "module": module,
                "sort": sort,
            }

        for intent, patterns in INTENT_PATTERNS.items():

            for pattern in patterns:

                if re.search(pattern, q):

                    return {
                        "intent": intent,
                        "module": module,
                    }

        return None