from typing import Dict, Any
from new_backend.ai.intent_detector import IntentDetector
from new_backend.ai.search_detector import SearchDetector
from new_backend.ai.module_detector import ModuleDetector
from new_backend.ai.sort_detector import SortDetector
from new_backend.ai.filter_detector import FilterDetector
from new_backend.ai.table_detector import TableDetector
from new_backend.ai.update_detector import UpdateDetector
from new_backend.ai.delete_detector import DeleteDetector
from new_backend.ai.create_detector import CreateDetector
from new_backend.ai.visualization_detector import VisualizationDetector
from new_backend.ai.selected_record_detector import SelectedRecordDetector


class QueryUnderstanding:

    @staticmethod
    def understand_query(
        query: str,
        current_module: str = None
    ) -> Dict[str, Any]:

        result = {

            "operation": "general_chat",

            "module": None,

            "search": None,

            "sort": None,

            "filter": None,
            "visualization": None,
            "table_columns": None, 
            "update": None,
            "delete": None,
            "create": None,
            "intent": None,

            "needs_llm": True

        }

        module = ModuleDetector.detect_module(query)
        print("Detected module =", module)
        print("Current module =", current_module)

        # Keep the current module for follow-up queries unless
        # the user explicitly mentions another CRM module.

        q = query.lower()

        explicit_module = any(
            word in q
            for word in [
                "lead",
                "leads",
                "contact",
                "contacts",
                "account",
                "accounts",
                "deal",
                "deals",
            ]
        )

        if current_module and not explicit_module:
            module = current_module

        elif not module and current_module:
            module = current_module

        if not module:

            q = query.lower()

            if "amount" in q or "stage" in q or "deal" in q:
                module = "Deals"

            elif "lead" in q:
                module = "Leads"

            elif "account" in q or "industry" in q:
                module = "Accounts"

            elif "contact" in q:
                module = "Contacts"
        

        if module:
            result["module"] = module

            result["table_columns"] = TableDetector.detect_table_columns(
                query,
                module
            )
            
        intent = IntentDetector.detect_intent(query)

        if intent:
            result["intent"] = intent
            
        # If module was not detected but intent knows it,
        # use the module from the intent.

        if not result["module"] and intent and intent.get("module"):
            result["module"] = intent["module"]

            result["table_columns"] = TableDetector.detect_table_columns(
                query,
                result["module"]
            )
            
            
        # ---------------- UPDATE ----------------

        update_data = UpdateDetector.extract_update_details_deterministic(query)

        if update_data:

            result["operation"] = "update"
            result["update"] = update_data
            result["needs_llm"] = False
            return result
        
        # ---------------- DELETE ----------------

        delete_data = DeleteDetector.extract_delete_details(query)

        if delete_data:

            result["operation"] = "delete"

            result["delete"] = delete_data

            result["needs_llm"] = False

            return result
        
        # ---------------- CREATE ----------------

        create_data = CreateDetector.extract_create_details(query)

        if create_data:

            result["operation"] = "create"

            result["create"] = create_data

            result["needs_llm"] = False

            return result
        
        selected_record = SelectedRecordDetector.detect(query)

        if selected_record:

            result["operation"] = "selected_record_field"

            result["search"] = selected_record

            result["needs_llm"] = False

            return result

        # ---------------- VISUALIZATION ----------------

        visualization = VisualizationDetector.detect_visualization(query)

        if visualization:
            result["visualization"] = visualization
            
        
        

            # If a CRM module is detected, this is still a SHOW operation
            
            # Do not decide the operation here.
            # Let Search/Filter/Sort continue first.
            # if module:
            #     result["operation"] = "show"    
            # else:
            #     result["operation"] = "analytics"

            # result["needs_llm"] = False
            

        # ---------------- SORT ----------------

        sort = SortDetector.detect_sort(query)

        if sort:

            result["operation"] = "sort"
            result["sort"] = sort
            result["needs_llm"] = False
            return result


        # ---------------- FILTER ----------------

        filter_data = FilterDetector.detect_filter(query)

        if filter_data:

            result["operation"] = "filter"
            result["filter"] = filter_data
            result["needs_llm"] = False
            return result
        
        # Column-only requests should use SHOW.
        # If the query also contains "details", "named", etc.,
        # let SearchDetector handle it.

        if result["table_columns"]:

            q = query.lower()

            detail_words = [
                "detail",
                "details",
                "record",
                "named",
                "called",
                "about",
            ]

            has_detail = any(word in q for word in detail_words)

            if (
                not has_detail
                and (
                    q.startswith("show")
                    or q.startswith("display")
                    or q.startswith("list")
                    or q.startswith("give")
                    or q.startswith("view")
                )
            ):

                result["operation"] = "show"
                result["needs_llm"] = False
                return result
        # ---------------- SEARCH ----------------

        search = SearchDetector.detect_search(query)

        if search:

            # If visualization exists, don't treat chart keywords as search
            if result["visualization"]:
                search = None
            else:
                result["operation"] = "search"
                result["search"] = search
                result["needs_llm"] = False
                return result
        
        # ---------------- CONTEXTUAL SHOW SEARCH ----------------

        q = query.lower().strip()

        show_keywords = {
            "all", "first", "last", "page", "pages",
            "record", "records", "where",
            "chart", "graph", "dashboard",
            "analytics", "summary",
            "column", "columns",
        }

        starts_with_show = q.startswith(("show ", "display ", "get "))

        navigation_words = {
            "all",
            "first",
            "last",
            "page",
            "pages",
            "record",
            "records",
            "top",
            "bottom",
        }

        if (
            starts_with_show
            and current_module
            and not result["filter"]
            and not result["sort"]
            and not result["table_columns"]
            and not result["visualization"]
            and not any(word in q.split() for word in navigation_words)
        ):

            remaining = SearchDetector.extract_clean_search_term(query)

            if (
                remaining
                and remaining.lower() not in show_keywords
                and len(remaining.split()) >= 1
            ):

                result["operation"] = "search"

                result["search"] = {
                    "module": current_module,
                    "search_term": remaining,
                    "value": remaining,
                }

                result["needs_llm"] = False

                return result

        
        # ---------------- SHOW ----------------

        if module:

            result["operation"] = "show"
            result["needs_llm"] = False
            
        elif result["visualization"]:

            result["operation"] = "show"
            result["needs_llm"] = False

        return result
            