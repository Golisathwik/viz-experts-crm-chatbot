from typing import Dict, Any

from new_backend.ai.query_understanding import QueryUnderstanding
from new_backend.services.crm_service import CRMService
from new_backend.services.cache_service import CacheService
from new_backend.services.crm_context_service import CRMContextService
from new_backend.services.visualization_engine import VisualizationEngine
from new_backend.services.navigation_service import NavigationService
from new_backend.services.search_service import SearchService
from new_backend.services.filter_service import FilterService
from new_backend.services.sort_service import SortService
from new_backend.services.update_service import UpdateService
from new_backend.services.delete_service import DeleteService
from new_backend.services.create_service import CreateService
from new_backend.ai.create_field_extractor import CreateFieldExtractor
from new_backend.repositories.action_repository import ActionRepository
from new_backend.ai.response_generation import ResponseGeneration
from new_backend.services.pagination_service import PaginationService



class ReadService:

    def __init__(self, crm_service: CRMService):

        self.crm = crm_service
        self.crm_context = CRMContextService()
        self.visualization = VisualizationEngine()
        

    def _post_process(
        self,
        session_id: int,
        module: str,
        records,
        understanding,
    ):

        # Clean CRM payload
        records = self.crm_context.optimize_records(records)

        # Cache dataset
        self.crm_context.cache_dataset(
            session_id=session_id,
            module=module,
            records=records,
            understanding=understanding,
        )

        return records
    
    async def execute(
        self,
        query: str,
        session_id: int,
        api_keys=None,
        current_module=None,
    ) -> Dict[str, Any]:
        
        pending_action = ActionRepository.get_active_pending_action(session_id)

        if pending_action:

            if pending_action["action_type"] == "UPDATE":

                return UpdateService.handle_update_workflow(
                    session_id=session_id,
                    user_input=query,
                    active_action=pending_action,
                    client=self.crm,
                )

            elif pending_action["action_type"] == "DELETE":

                return DeleteService.handle_delete_workflow(
                    session_id=session_id,
                    user_input=query,
                    active_action=pending_action,
                    client=self.crm,
                )
            
            elif pending_action["action_type"] == "CREATE":

                return CreateService.handle_create_workflow(
                    session_id=session_id,
                    user_input=query,
                    active_action=pending_action,
                    client=self.crm,
                )
                
        # ------------------------------------------
        # Navigation Commands
        # ------------------------------------------

        if NavigationService.is_navigation_query(query):

            navigation = NavigationService.handle(
                session_id=session_id,
                query=query,
            )

            if navigation:
                if navigation["navigation"] == "record":
                    return {
                        "success": True,
                        "operation": "record",
                        "module": CacheService.get_state(session_id)["current_module"],
                        "response": {
                            "summary": ResponseGeneration.generate_detail_view(
                                module=CacheService.get_state(session_id)["current_module"],
                                record=navigation["record"],
                            ),
                            "kpis": None,
                            "table": None,
                            "chart": None,
                            "suggestions": ResponseGeneration.generate_suggestions(
                                query=query,
                                module=CacheService.get_state(session_id)["current_module"],
                                records=[navigation["record"]],
                            ),
                        },
                        "records": [navigation["record"]],
                        "pagination": PaginationService.get_metadata(session_id),
                    }

                records = navigation["records"]
                state = CacheService.get_state(session_id)
                module = state.get("current_module")

                table = None

                if len(records) > 1:
                    table = self.visualization.build_table(
                        module=module,
                        records=records,
                        columns=None,
                        understanding=None,
                    )

                kpis = None

                summary = (
                    f"Showing records "
                    f"{navigation['start']}–{navigation['end']} "
                    f"of {navigation['total']}."
                )

                return {
                    "success": True,
                    "operation": "navigation",
                    "module": module,
                    "response": {
                        "summary": summary,
                        "kpis": kpis,
                        "table": table,
                        "chart": None,
                        "suggestions": [],
                    },
                    "records": records,
                    "table": table,
                    "chart": None,
                    "pagination": PaginationService.get_metadata(session_id),
                }

        understanding = QueryUnderstanding.understand_query(
            query,
            current_module=current_module,
        )
        print("UNDERSTANDING =", understanding)
        print("CURRENT MODULE =", current_module)
        print("TABLE =", understanding.get("table_columns"))

        operation = understanding["operation"]

        module = understanding["module"]
        # ----------------------------------------------------
        # Convert "show <record>" into SEARCH
        # ----------------------------------------------------

        tokens = query.lower().strip().split()

        if (
            operation == "show"
            and module is None
            and len(tokens) >= 2
        ):
            understanding["operation"] = "search"

            understanding["search"] = {
                "module": "All",
                "search_term": " ".join(tokens[1:]),
                "value": " ".join(tokens[1:]),
                "requested_fields": [],
                "details": False,
            }

            operation = "search"
            module = "All"
        
        # For search requests, the detector may resolve the module
        # inside the search object (e.g. "All").
        if (
            operation == "search"
            and understanding.get("search")
            and understanding["search"].get("module")
        ):
            module = understanding["search"]["module"]
            
            

        # ----------------------------------------------------
        # SHOW
        # ----------------------------------------------------

        if operation == "show":

            state = CacheService.get_state(session_id)

            # ----------------------------------------------------
            # Detect explicit "show all <module>" request
            # ----------------------------------------------------
            normalized_query = " ".join(query.lower().strip().split())

            explicit_all_request = (
                f"all {module.lower()}" in normalized_query
                or normalized_query == f"show all {module.lower()}"
                or normalized_query == f"show all {module.lower()} details"
            )

            # ----------------------------------------------------
            # Follow-up column request
            #
            # IMPORTANT:
            # Do NOT reuse cached_dataset for explicit "show all"
            # requests because cached_dataset may contain only a
            # previous search/detail result.
            # ----------------------------------------------------
            if (
                current_module
                and module == current_module
                and understanding.get("table_columns")
                and state.get("cached_dataset")
                and not explicit_all_request
            ):
                records = state["cached_dataset"]

            else:

                # Explicit "show all" must always use the complete
                # CRM dataset instead of the previous search cache.
                if module == "Leads":
                    records = self.crm.get_leads()

                elif module == "Contacts":
                    records = self.crm.get_contacts()

                elif module == "Accounts":
                    records = self.crm.get_accounts()

                elif module == "Deals":
                    records = self.crm.get_deals()

                else:
                    records = []

            if not state.get("cached_dataset") or records is not state.get("cached_dataset"):
                records = self._post_process(
                    session_id=session_id,
                    module=module,
                    records=records,
                    understanding=understanding,
                )
            state = CacheService.get_state(session_id)

            state["current_module"] = module
            state["cached_dataset"] = records
            pagination = {
                "page": 1,
                "page_size": len(records),
                "total_records": len(records),
                "total_pages": 1,
            }

            table = None

            if len(records) > 1:
                print("TABLE COLUMNS =", understanding.get("table_columns"))

                table = self.visualization.build_table(
                    module=module,
                    records=records,
                    columns=understanding.get("table_columns"),
                    understanding=understanding,
                )

            if len(records) == 1:
                kpis = None

                state["selected_record"] = records[0]
                state["selected_record_data"] = records[0]
                state["selected_record_id"] = records[0].get("id")
                state["selected_record_module"] = module
                
            else:
                kpis = self.visualization.build_kpis(
                    records,
                    module,
                )
            if len(records) == 1:

                summary = ResponseGeneration.generate_detail_view(
                    module=module,
                    record=records[0],
                )

            else:

                summary = ResponseGeneration.generate_summary(
                    query=query,
                    module=module,
                    records=records,
                    kpis=kpis,
                )

            suggestions = ResponseGeneration.generate_suggestions(
                query=query,
                module=module,
                records=records,
            )
            if len(records) > 1 and module in [
                "Leads",
                "Contacts",
                "Accounts",
                "Deals",
            ]:

                chart = self.visualization.build_dashboard(
                    module=module,
                    records=records,
                )

            else:

                chart = None

            return {
                "success": True,

                "operation": operation,

                "module": module,

                "response": {
                    "summary": summary,
                    "kpis": kpis,
                    "table": table,
                    "chart": chart,
                    "suggestions": suggestions,
                },

                "records": records,

                "table": table,

                "chart": chart,

                "pagination": pagination,

                "query": understanding,
            }
            
        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        if operation == "search":

            search = understanding["search"]

            term = search["search_term"]
            print("SEARCH OPERATION")
            print("TERM =", term)
            print("MODULE =", module)
            # -----------------------------
            # Search current module first
            # -----------------------------
            search_module = None if module == "All" else module

            records = SearchService.perform_prioritized_search(
                client=self.crm,
                query=term,
                detected_module=search_module,
                user_query=query,
                session_id=session_id,
            )

            # -----------------------------------------
            # Not found in current module?
            # Search globally.
            # -----------------------------------------
            if (
                search_module is not None
                and not records
            ):
                print(
                    f"'{term}' not found in {search_module}. "
                    "Trying global search..."
                )

                records = SearchService.perform_prioritized_search(
                    client=self.crm,
                    query=term,
                    detected_module=None,
                    user_query=query,
                    session_id=session_id,
                )

                if records:
                    module = "Global Search"
            
            # SearchService returns (module, record) tuples.
            # Visualization, analytics and cache expect only record dictionaries.
            if records and isinstance(records[0], tuple):

                if module == "All":
                    module = "Global Search"

                converted = []

                for module_name, record in records:

                    record = dict(record)      # copy

                    record["_module"] = module_name

                    # Create a common Name field for display
                    if "Name" not in record:

                        if record.get("First_Name") or record.get("Last_Name"):
                            record["Name"] = (
                                f"{record.get('First_Name','')} "
                                f"{record.get('Last_Name','')}"
                            ).strip()

                        elif record.get("Deal_Name"):
                            record["Name"] = record["Deal_Name"]

                        elif record.get("Account_Name"):
                            record["Name"] = record["Account_Name"]

                        elif record.get("Full_Name"):
                            record["Name"] = record["Full_Name"]

                    converted.append(record)

                records = converted
                
            records = self._post_process(
                session_id=session_id,
                module=module,
                records=records,
                understanding=understanding,
            )
            state = CacheService.get_state(session_id)
            # Cache search results
            state["cached_dataset"] = records
            pagination = {
                "page": 1,
                "page_size": len(records),
                "total_records": len(records),
                "total_pages": 1,
            }

            if len(records) > 1:

                state["pending_record_selection"] = True
                state["pending_records"] = records
                state["current_module"] = module

            elif len(records) == 1:

                state["pending_record_selection"] = None
                state["pending_records"] = []
                state["current_module"] = module

                state["selected_record"] = records[0]
                state["selected_record_data"] = records[0]
                state["selected_record_id"] = records[0].get("id")
                state["selected_record_module"] = (
                    records[0].get("_module") or module
                )
            
            if module == "All":
                module = "Global Search"

            table = None

            if len(records) > 1:
                print("TABLE COLUMNS =", understanding.get("table_columns"))
                table = self.visualization.build_table(
                    module=module,
                    records=records,
                    columns=understanding.get("table_columns"),
                    understanding=understanding,
                )

            if len(records) == 1:
                kpis = None

            elif module == "Global Search":
                kpis = None

            else:
                kpis = self.visualization.build_kpis(
                    records,
                    module,
                )
                
            if len(records) == 1:

                summary = ResponseGeneration.generate_detail_view(
                    module=module,
                    record=records[0],
                )

            else:

                summary = ResponseGeneration.generate_summary(
                    query=query,
                    module=module,
                    records=records,
                    kpis=kpis,
                )

            suggestions = ResponseGeneration.generate_suggestions(
                query=query,
                module=module,
                records=records,
            )

            if len(records) > 1 and module in [
                "Leads",
                "Contacts",
                "Accounts",
                "Deals",
            ]:

                chart = self.visualization.build_dashboard(
                    module=module,
                    records=records,
                )

            else:

                chart = None
                
            print("\n===== SEARCH RESPONSE =====")
            print(summary)
            print("===========================\n")

            return {
                "success": True,

                "operation": operation,

                "module": module,

                "response": {
                    "summary": summary,
                    "kpis": kpis,
                    "table": table,
                    "chart": chart,
                    "suggestions": suggestions,
                },

                "records": records,

                "table": table,

                "chart": chart,
                
                "pagination": pagination,

                "query": understanding,
            }

        # ----------------------------------------------------
        # SORT
        # ----------------------------------------------------

        if operation == "sort":

            session_id = session_id

            state = CacheService.get_state(session_id)
            if module is None:
                module = state.get("current_module")

            # Use previous module if the parser didn't detect one
            if module is None:
                module = state.get("current_module")

            # Always sort from the original dataset, not the filtered dataset
            if module == state.get("current_module"):
                records = state.get("raw_cached_dataset", [])
            else:
                records = state.get("raw_module_cache", {}).get(module, [])

            # Fallback for older sessions
            if not records:
                if module == state.get("current_module"):
                    records = state.get("cached_dataset", [])
                else:
                    records = state.get("module_cache", {}).get(module, [])
            # Cache miss → fetch from CRM
            if not records:

                if module == "Leads":
                    records = self.crm.get_leads()

                elif module == "Contacts":
                    records = self.crm.get_contacts()

                elif module == "Accounts":
                    records = self.crm.get_accounts()

                elif module == "Deals":
                    records = self.crm.get_deals()

                else:
                    records = []

                records = self._post_process(
                    session_id=session_id,
                    module=module,
                    records=records,
                    understanding=understanding,
                )

            records = SortService.apply_sort(
                records,
                module,
                understanding["sort"],
            )
            # Cache sorted dataset
            state["cached_dataset"] = records
            pagination = {
                "page": 1,
                "page_size": len(records),
                "total_records": len(records),
                "total_pages": 1,
            }
            table = None

            if len(records) > 1:

                table = self.visualization.build_table(
                    module=module,
                    records=records,
                    columns=understanding.get("table_columns"),
                    understanding=understanding,
                )

            if len(records) == 1:
                kpis = None
            else:
                kpis = self.visualization.build_kpis(
                    records,
                    module,
                )

            if len(records) == 1:

                summary = ResponseGeneration.generate_detail_view(
                    module=module,
                    record=records[0],
                )

            else:

                summary = ResponseGeneration.generate_summary(
                    query=query,
                    module=module,
                    records=records,
                    kpis=kpis,
                )

            suggestions = ResponseGeneration.generate_suggestions(
                query=query,
                module=module,
                records=records,
            )

            return {
                "success": True,

                "operation": operation,

                "module": module,

                "response": {
                    "summary": summary,
                    "kpis": kpis,
                    "table": table,
                    "chart": None,
                    "suggestions": suggestions,
                },

                "records": records,

                "table": table,

                "chart": None,

                "pagination": pagination,

                "query": understanding,
            }

        # ----------------------------------------------------
        # FILTER
        # ----------------------------------------------------

        if operation == "filter":

            session_id = session_id

            state = CacheService.get_state(session_id)
            if module is None:
                module = state.get("current_module")

            # Use previous module if the parser didn't detect one
            if module is None:
                module = state.get("current_module")

            if module == state.get("current_module"):
                records = state.get("raw_cached_dataset", [])
            else:
                records = state.get("raw_module_cache", {}).get(module, [])
                
            # Cache miss → fetch from CRM
            if not records:

                if module == "Leads":
                    records = self.crm.get_leads()

                elif module == "Contacts":
                    records = self.crm.get_contacts()

                elif module == "Accounts":
                    records = self.crm.get_accounts()

                elif module == "Deals":
                    records = self.crm.get_deals()

                else:
                    records = []

                records = self._post_process(
                    session_id=session_id,
                    module=module,
                    records=records,
                    understanding=understanding,
                )

            filter_data = understanding["filter"]
            print("\n========== FILTER DEBUG ==========")
            print("Query:", query)
            print("Understanding Filter:", understanding.get("filter"))
            print("Records before filter:", len(records))
            print("==================================")

            records = FilterService.apply_filter(
                records=records,
                module=module,
                filter_request=filter_data,
            )
            print("Records after filter:", len(records))
            print("==================================\n")
            # Cache filtered dataset
            state["cached_dataset"] = records
            pagination = {
                "page": 1,
                "page_size": len(records),
                "total_records": len(records),
                "total_pages": 1,
            }

            table = None

            if len(records) > 1:

                table = self.visualization.build_table(
                    module=module,
                    records=records,
                    columns=understanding.get("table_columns"),
                    understanding=understanding,
                )

            if len(records) == 1:
                kpis = None
            else:
                kpis = self.visualization.build_kpis(
                    records,
                    module,
                )

            if len(records) == 1:

                summary = ResponseGeneration.generate_detail_view(
                    module=module,
                    record=records[0],
                )

            else:

                summary = ResponseGeneration.generate_summary(
                    query=query,
                    module=module,
                    records=records,
                    kpis=kpis,
                )

            suggestions = ResponseGeneration.generate_suggestions(
                query=query,
                module=module,
                records=records,
            )

            return {
                "success": True,

                "operation": operation,

                "module": module,

                "response": {
                    "summary": summary,
                    "kpis": kpis,
                    "table": table,
                    "chart": None,
                    "suggestions": suggestions,
                },

                "records": records,

                "table": table,

                "chart": None,

                "pagination": pagination,

                "query": understanding,
            }
            
            
        # ----------------------------------------------------
        # UPDATE
        # ----------------------------------------------------

        if operation == "update":

            update_data = understanding.get("update", {})

            extracted_fields = {}

            try:

                extracted_fields = await CreateFieldExtractor.extract_fields(
                    module=current_module,
                    user_text=query,
                    api_keys=api_keys,
                ) or {}

            except Exception as e:

                print("Update Field Extraction Error:", e)

                extracted_fields = {}

            return UpdateService.start_update(
                session_id=session_id,
                target_record=update_data.get("target_record"),
                raw_field=update_data.get("field_name"),
                new_value=update_data.get("new_value"),
                extracted_fields=extracted_fields,
                client=self.crm,
                user_query=query,
            )  
        
        # ----------------------------------------------------
        # DELETE
        # ----------------------------------------------------

        if operation == "delete":

            delete_data = understanding.get("delete", {})

            return DeleteService.start_delete(
                session_id=session_id,
                target_record=delete_data.get("target_record"),
                module=delete_data.get("module"),
                client=self.crm,
                user_query=query,
            )   
        
        # ----------------------------------------------------
        # CREATE
        # ----------------------------------------------------

        if operation == "create":

            create_data = understanding.get("create", {})

            return CreateService.start_create(
                session_id=session_id,
                create_data=create_data,
                client=self.crm,
                user_query=query,
            ) 
            

        return {
            "operation": "general_chat",
            "query": understanding
        }
        
        
        