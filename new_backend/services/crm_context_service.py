from typing import Any, Dict, List
import json
from new_backend.services.cache_service import CacheService

class CRMContextService:

    @staticmethod
    def clean_crm_record(record: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(record, dict):
            return record

        cleaned = {}

        for key, value in record.items():

            # Remove internal Zoho fields
            if key.startswith("$"):
                continue

            if key == "Record_Image":
                continue

            if value is None or value == "":
                continue

            # Flatten common nested objects
            if key == "Owner" and isinstance(value, dict):
                cleaned["Owner_Name"] = value.get("name")
                continue

            if key == "Created_By" and isinstance(value, dict):
                cleaned["Created_By_Name"] = value.get("name")
                continue

            if key == "Modified_By" and isinstance(value, dict):
                cleaned["Modified_By_Name"] = value.get("name")
                continue

            cleaned[key] = value

        return cleaned

    @staticmethod
    def clean_crm_data(data):

        if isinstance(data, list):
            return [
                CRMContextService.clean_crm_record(item)
                for item in data
            ]

        if isinstance(data, dict):
            return CRMContextService.clean_crm_record(data)

        return data

    @staticmethod
    def optimize_records(records: List[Dict]):

        if not records:
            return []

        cleaned = CRMContextService.clean_crm_data(records)

        optimized = []

        seen = set()

        for record in cleaned:

            if not isinstance(record, dict):
                optimized.append(record)
                continue

            record_id = record.get("id")

            if record_id:

                if record_id in seen:
                    continue

                seen.add(record_id)

            optimized.append(record)

        return optimized
    
    
    @staticmethod
    def prepare_llm_context(records: List[Dict]) -> str:
        """
        Creates a lightweight CRM context for the LLM.
        """

        optimized = CRMContextService.optimize_records(records)

        final_records = []

        excluded_keywords = {
            "owner",
            "approval",
            "review",
            "system",
            "image",
            "$",
        }

        for record in optimized:

            cleaned = {}

            for key, value in record.items():

                key_lower = key.lower()

                if any(x in key_lower for x in excluded_keywords):
                    continue

                cleaned[key] = value

            final_records.append(cleaned)

        return json.dumps(
            final_records,
            indent=2,
            ensure_ascii=False,
        )

    @staticmethod
    def reduce_for_reasoning(records: List[Dict]) -> List[Dict]:
        """
        Keeps only business fields for reasoning models.
        """

        allowed = {
            "name",
            "full_name",
            "first_name",
            "last_name",
            "lead_name",
            "deal_name",
            "account_name",
            "company",
            "email",
            "phone",
            "mobile",
            "industry",
            "website",
            "stage",
            "status",
            "lead_status",
            "amount",
            "annual_revenue",
            "revenue",
            "closing_date",
            "description",
            "rating",
        }

        reduced = []

        for record in records:

            cleaned = {}

            for key, value in record.items():

                if value in ("", None):
                    continue

                key_lower = key.lower()

                if any(
                    field == key_lower or field in key_lower
                    for field in allowed
                ):
                    cleaned[key] = value

            reduced.append(cleaned)

        return reduced
    
    @staticmethod
    def cache_dataset(
        session_id: int,
        module: str,
        records: List[Dict],
        understanding: Dict,
    ) -> None:
        """
        Store the current CRM dataset in the session cache.
        """

        CacheService.update_cache(
            session_id=session_id,
            module=module,
            records=records,
            raw_records=records,
            intent=understanding.get("intent"),
            query=understanding,
            query_term=(
                understanding.get("search", {}) or {}
            ).get("search_term"),
        )
     
    @staticmethod
    def sync_cache_record(
        session_id: int,
        module: str,
        record_id: str,
        fresh_record: dict,
    ):
        state = CacheService.get_state(session_id)

        if state.get("current_module") == module:
            for i, rec in enumerate(state.get("cached_dataset", [])):
                if str(rec.get("id")) == str(record_id):
                    state["cached_dataset"][i] = fresh_record
                    break

            for i, rec in enumerate(state.get("raw_cached_dataset", [])):
                if str(rec.get("id")) == str(record_id):
                    state["raw_cached_dataset"][i] = fresh_record
                    break

        module_cache = state.setdefault("module_cache", {})
        if module in module_cache:
            for i, rec in enumerate(module_cache[module]):
                if str(rec.get("id")) == str(record_id):
                    module_cache[module][i] = fresh_record
                    break

        raw_module_cache = state.setdefault("raw_module_cache", {})
        if module in raw_module_cache:
            for i, rec in enumerate(raw_module_cache[module]):
                if str(rec.get("id")) == str(record_id):
                    raw_module_cache[module][i] = fresh_record
                    break