from typing import List, Dict, Any


class ResponseGeneration:

    @staticmethod
    def generate_summary(
        query: str,
        module: str,
        records: List[Dict[str, Any]],
        kpis: Dict[str, Any],
    ):

        if not records:
            return f"No {module.lower()} found."

        total = len(records)
        
        # -----------------------------
        # SINGLE RECORD SUMMARY
        # -----------------------------


        # -----------------------------
        # SEARCH SUMMARY
        # -----------------------------
        query_lower = (query or "").strip().lower()

        if (
            query_lower.startswith("search")
            or (
                query_lower.startswith("show ")
                and "details" in query_lower
            )
        ):

            # If multiple matches, ask the user to select one
            if total > 1:

                summary = [
                    f"I found **{total}** matching records.",
                    "",
                    "Please select one of the following:",
                    ""
                ]

                for index, record in enumerate(records, start=1):

                    module_name = record.get("_module") or module

                    # Convert Leads -> Lead, Contacts -> Contact, etc.
                    if module_name.endswith("s"):
                        module_name = module_name[:-1]

                    name = (
                        record.get("Name")
                        or f"{record.get('First_Name','')} {record.get('Last_Name','')}".strip()
                        or record.get("Deal_Name")
                        or record.get("Account_Name")
                        or record.get("Company")
                        or "Unknown"
                    )

                    company = (
                        record.get("Company")
                        or record.get("Account_Name")
                        or "-"
                    )

                    summary.append(f"{index}. **{name}** ({module_name})")
                    summary.append(f"   Company: {company}")
                    summary.append("")

                summary.append(
                    "Reply with the record number "
                    "(for example: **1** or **2**) "
                    "to view the complete details."
                )

                return "\n".join(summary)

            modules = {}

            for r in records:
                m = r.get("_module", module)
                modules[m] = modules.get(m, 0) + 1

            module_text = ", ".join(
                f"{count} {name}"
                for name, count in modules.items()
            )

            return (
                f"I found {total} matching record across {module_text}."
            )
            
        # -----------------------------
        # FILTER SUMMARY
        # -----------------------------
        if query.lower().startswith("filter"):

            return (
                f"I found {total} matching "
                f"{module.lower()} "
                f"{'record' if total == 1 else 'records'}. "
                f"The filtered results are shown below."
            )


        # -----------------------------
        # SORT SUMMARY
        # -----------------------------
        if query.lower().startswith("sort"):

            return (
                f"I sorted {total} "
                f"{module.lower()} "
                f"{'record' if total == 1 else 'records'}. "
                f"The sorted results are shown below."
            )

        if module == "Leads":

            contacted = kpis.get("contacted", 0)
            lost = kpis.get("lost", 0)
            junk = kpis.get("junk", 0)

            return (
                f"The CRM currently contains {total} lead records. "
                f"{contacted} leads have already been contacted, "
                f"{lost} have been marked as lost, and "
                f"{junk} are classified as junk leads. "
                f"The remaining leads are active prospects. "
                f"The detailed information is available in the table below."
            )

        if module == "Deals":

            return (
                f"The CRM currently contains {total} deals. "
                f"The pipeline statistics and deal information "
                f"are shown below together with KPIs."
            )

        if module == "Accounts":

            return (
                f"The CRM currently contains {total} customer accounts. "
                f"The account details and business information "
                f"are displayed below."
            )

        if module == "Contacts":

            return (
                f"The CRM currently contains {total} contacts. "
                f"The complete contact information "
                f"is displayed in the table below."
            )

        return f"Found {total} records."
    
    @staticmethod
    def generate_detail_view(
        module: str,
        record: Dict[str, Any],
    ):

        ignore = {
            "_module",
            "id",
            "Created_Time",
            "Modified_Time",
            "Created_By",
            "Modified_By",
            "Tag",
            "$currency_symbol",
            "$process_flow",
            "$approval",
            "$review_process",
            "$editable",
            "$orchestration",
            "$approval_state",
        }

        if module == "Leads":
            title = (
                record.get("Name")
                or f"{record.get('First_Name','')} {record.get('Last_Name','')}".strip()
                or "Unknown"
            )
            heading = f"# Lead Details\n\n**{title}**"

        elif module == "Contacts":
            heading = f"# Contact Details\n\n**{record.get('Name','Unknown')}**"

        elif module == "Accounts":
            heading = f"# Account Details\n\n**{record.get('Account_Name','Unknown')}**"

        elif module == "Deals":
            heading = f"# Deal Details\n\n**{record.get('Deal_Name','Unknown')}**"

        else:
            heading = "# Record Details"

        priority = [
            "Company",
            "Account_Name",
            "Deal_Name",
            "Stage",
            "Lead_Status",
            "Industry",
            "Phone",
            "Mobile",
            "Email",
            "Annual_Revenue",
            "Amount",
            "Closing_Date",
            "Website",
            "Owner",
        ]

        lines = [heading, ""]

        shown = set()

        for field in priority:

            if field in record and record[field]:

                value = record[field]

                if isinstance(value, dict):
                    value = value.get("name", value)

                lines.append(
                    f"**{field.replace('_',' ')}:** {value}"
                )

                shown.add(field)

        for field, value in record.items():

            if (
                field in shown
                or field in ignore
                or value in ("", None, [], {})
                or field.startswith("$")
            ):
                continue

            if isinstance(value, dict):
                value = value.get("name", value)

            lines.append(
                f"**{field.replace('_',' ')}:** {value}"
            )

        return "\n\n".join(lines)

    @staticmethod
    def generate_suggestions(
        query: str,
        module: str,
        records: List[Dict[str, Any]],
    ):

        query_lower = (query or "").strip().lower()
        total = len(records or [])

        # Normalize module name
        module_name = module or "records"

        if module_name.endswith("s"):
            singular_module = module_name[:-1]
        else:
            singular_module = module_name

        # ------------------------------------------------------------------
        # SINGLE RECORD SUGGESTIONS
        # ------------------------------------------------------------------
        # IMPORTANT:
        # Keep this block first so selected-record operations continue to
        # work exactly as before.
        # ------------------------------------------------------------------

        if len(records) == 1 and isinstance(records[0], dict):

            record = records[0]
            suggestions = []

            # --------------------------------------------------------------
            # LEADS
            # --------------------------------------------------------------
            if module_name == "Leads":

                suggestions.extend([
                    "Show phone number",
                    "Show full name",
                    "Show email ID",
                    "Add more",
                ])

                if record.get("Phone"):
                    suggestions.append("Change phone number")

                if record.get("Email"):
                    suggestions.append("Change email ID")

                return suggestions

            # --------------------------------------------------------------
            # CONTACTS
            # --------------------------------------------------------------
            elif module_name == "Contacts":

                suggestions.extend([
                    "Show phone number",
                    "Show full name",
                    "Show email ID",
                    "Add more",
                ])

                if record.get("Phone") or record.get("Mobile"):
                    suggestions.append("Change phone number")

                if record.get("Email"):
                    suggestions.append("Change email ID")

                return suggestions

            # --------------------------------------------------------------
            # ACCOUNTS
            # --------------------------------------------------------------
            elif module_name == "Accounts":

                suggestions.extend([
                    "Show phone number",
                    "Show account name",
                ])

                if record.get("Email"):
                    suggestions.append("Show email ID")

                suggestions.append("Add more")

                if record.get("Phone"):
                    suggestions.append("Change phone number")

                if record.get("Email"):
                    suggestions.append("Change email ID")

                return suggestions

            # --------------------------------------------------------------
            # DEALS
            # --------------------------------------------------------------
            elif module_name == "Deals":

                suggestions.append("Show deal name")

                if record.get("Phone"):
                    suggestions.append("Show phone number")

                if record.get("Email"):
                    suggestions.append("Show email ID")

                suggestions.append("Add more")

                if record.get("Phone"):
                    suggestions.append("Change phone number")

                if record.get("Email"):
                    suggestions.append("Change email ID")

                return suggestions

        # ------------------------------------------------------------------
        # SEARCH SUGGESTIONS
        # ------------------------------------------------------------------
        # Keep the existing search suggestions.
        # Do not expose the actual searched value.
        # ------------------------------------------------------------------

        if (
            query_lower.startswith("search")
            or (
                query_lower.startswith("show ")
                and "details" in query_lower
            )
        ):
            return [
                "Search for a name",
                "Search for an email ID",
                "Search for a phone number",
                "Show records 10 to 20",
            ]

        # ------------------------------------------------------------------
        # RECORD NAVIGATION
        # ------------------------------------------------------------------
        # Keep the existing navigation suggestions.
        # ------------------------------------------------------------------

        if (
            "show first" in query_lower
            or "show last" in query_lower
            or "show records" in query_lower
            or "show record" in query_lower
        ):
            return [
                "Show first 5",
                "Show last 5",
                "Show records 10 to 20",
                "Show record 7",
            ]

        # ------------------------------------------------------------------
        # FILTER SUGGESTIONS
        # ------------------------------------------------------------------
        # Keep the existing filter suggestions and add the supported
        # filter variations.
        # ------------------------------------------------------------------

        if (
            query_lower.startswith("filter")
            or " where " in f" {query_lower} "
            or query_lower.startswith("show revenue")
            or "contains" in query_lower
            or "starts with" in query_lower
            or "ends with" in query_lower
            or "greater than" in query_lower
            or "less than" in query_lower
            or "between" in query_lower
            or "closing date" in query_lower
        ):

            if module_name == "Deals":
                return [
                    "Show deals where closing date after 01-06-2026",
                    "Show deals where closing date after 7th June 2026",
                    "Show Amount greater than 5 lakhs",
                    "Sort by Amount",
                ]

            if module_name == "Accounts":
                return [
                    "Show company name where starts with A",
                    "Filter email contains gmail",
                    "Show Revenue greater than 5 lakhs",
                    "Show Revenue less than 10 lakhs",
                ]

            return [
                "Show company name where starts with A",
                "Filter email contains gmail",
                "Show names starts with letter k",
                "Show Revenue greater than 5 lakhs",
            ]

        # ------------------------------------------------------------------
        # SORT SUGGESTIONS
        # ------------------------------------------------------------------
        # Keep the existing sort suggestions and add supported variations.
        # ------------------------------------------------------------------

        if query_lower.startswith("sort"):

            if module_name == "Deals":
                return [
                    "Sort by Amount",
                    "Sort by names",
                    "Sort names in descending",
                    "Show amount column",
                ]

            if module_name == "Accounts":
                return [
                    "Sort by company",
                    "Sort by revenue",
                    "Sort revenue in descending",
                    "Show annual revenue column",
                ]

            return [
                "Sort by email",
                "Sort by phone number",
                "Sort by names",
                "Sort names in descending",
            ]

        # ------------------------------------------------------------------
        # GLOBAL "SHOW ALL <MODULE>"
        # ------------------------------------------------------------------
        # IMPORTANT:
        # This block comes BEFORE CREATE/UPDATE/DELETE/default.
        #
        # We combine:
        #   1. Existing record navigation suggestions
        #   2. Column suggestions
        #   3. Filter suggestions
        #   4. Sort suggestions
        #
        # Only a small deterministic set is returned.
        # Nothing here changes the actual CRM operation.
        # ------------------------------------------------------------------

        is_show_all = (
            "show all leads" in query_lower
            or "show all deals" in query_lower
            or "show all contacts" in query_lower
            or "show all accounts" in query_lower
        )

        if is_show_all:

            suggestions = []

            # --------------------------------------------------------------
            # 1. NAVIGATION
            # --------------------------------------------------------------

            if total >= 7:
                suggestions.append("Show record 7")
            elif total >= 1:
                suggestions.append("Show record 1")

            if total >= 10:
                suggestions.append("Show records 5 to 10")
            elif total >= 5:
                suggestions.append(
                    f"Show records 1 to {min(5, total)}"
                )

            # --------------------------------------------------------------
            # 2. MODULE-SPECIFIC COLUMN SUGGESTIONS
            # --------------------------------------------------------------

            if module_name == "Leads":

                column_suggestions = [
                    "Show names column",
                    "Show phone number column",
                    "Show phone number and email ID columns",
                    "Show annual revenue column",
                ]

                filter_suggestions = [
                    "Show company name where starts with A",
                    "Filter email contains gmail",
                    "Show names starts with letter k",
                    "Show Revenue greater than 5 lakhs",
                    "Show Revenue less than 10 lakhs",
                    "Show Revenue between 2 lakhs and 10 lakhs",
                    "Show Revenue between 200000 and 1000000",
                    "Show Revenue between 2.5 lakh and 8 lakh",
                ]

                sort_suggestions = [
                    "Sort by email",
                    "Sort by phone number",
                    "Sort by names",
                    "Sort by full name",
                    "Sort by company",
                    "Sort by revenue",
                    "Sort names in descending",
                    "Sort revenue in descending",
                    "Sort email in descending",
                ]

            elif module_name == "Deals":

                column_suggestions = [
                    "Show deal name column",
                    "Show amount column",
                    "Show closing date column",
                ]

                filter_suggestions = [
                    "Show deals where closing date after 2026-06-01",
                    "Show deals where closing date after 7th June 2026",
                    "Show Revenue greater than 5 lakhs",
                    "Show Revenue less than 10 lakhs",
                ]

                sort_suggestions = [
                    "Sort by Amount",
                    "Sort by names",
                    "Sort names in descending",
                    "Sort by email",
                ]

            elif module_name == "Accounts":

                column_suggestions = [
                    "Show account name column",
                    "Show phone number column",
                    "Show phone number and email ID columns",
                    "Show annual revenue column",
                ]

                filter_suggestions = [
                    "Show company name where starts with A",
                    "Filter email contains gmail",
                    "Show Revenue greater than 5 lakhs",
                    "Show Revenue less than 10 lakhs",
                    "Show Revenue between 2 lakhs and 10 lakhs",
                    "Show Revenue between 200000 and 1000000",
                ]

                sort_suggestions = [
                    "Sort by company",
                    "Sort by revenue",
                    "Sort revenue in descending",
                    "Sort email in descending",
                ]

            elif module_name == "Contacts":

                column_suggestions = [
                    "Show names column",
                    "Show phone number column",
                    "Show phone number and email ID columns",
                ]

                filter_suggestions = [
                    "Filter email contains gmail",
                    "Show names starts with letter k",
                    "Show company name where starts with A",
                ]

                sort_suggestions = [
                    "Sort by email",
                    "Sort by phone number",
                    "Sort by names",
                    "Sort by full name",
                    "Sort names in descending",
                ]

            else:

                column_suggestions = [
                    "Show names column",
                    "Show phone number column",
                    "Show email ID column",
                ]

                filter_suggestions = [
                    "Filter email contains gmail",
                    "Show names starts with letter k",
                ]

                sort_suggestions = [
                    "Sort by names",
                    "Sort by email",
                ]

            # --------------------------------------------------------------
            # 3. ADD ONE OR TWO COLUMNS
            # --------------------------------------------------------------

            for suggestion in column_suggestions[:2]:
                if len(suggestions) >= 5:
                    break
                suggestions.append(suggestion)

            # --------------------------------------------------------------
            # 4. ADD ONE FILTER
            # --------------------------------------------------------------

            if len(suggestions) < 5 and filter_suggestions:
                suggestions.append(filter_suggestions[0])

            # --------------------------------------------------------------
            # 5. ADD ONE SORT
            # --------------------------------------------------------------

            if len(suggestions) < 5 and sort_suggestions:
                suggestions.append(sort_suggestions[0])

            # --------------------------------------------------------------
            # 6. GUARANTEE AT LEAST A USEFUL RESULT
            # --------------------------------------------------------------

            if not suggestions:
                suggestions = [
                    "Show first 5",
                    "Show last 5",
                    "Show names column",
                    "Filter email contains gmail",
                    "Sort by names",
                ]

            return suggestions[:5]

        # ------------------------------------------------------------------
        # CREATE SUGGESTIONS
        # ------------------------------------------------------------------

        if (
            query_lower.startswith("create")
            or query_lower.startswith("add a new")
            or query_lower.startswith("add new")
        ):
            return [
                "Create a new lead named Rahul Sharma.",
                "Create a contact named John Smith.",
                "Create an account named ABC Technologies.",
                "Create a deal named Website Development.",
            ]

        # ------------------------------------------------------------------
        # UPDATE / RECORD DETAIL FLOW
        # ------------------------------------------------------------------
        # Keep the existing behavior untouched.
        # ------------------------------------------------------------------

        if (
            "change" in query_lower
            or "update" in query_lower
            or "add more" in query_lower
            or "available options" in query_lower
        ):
            return [
                "Show all leads",
                "Show record 7",
                "Show first 5",
                "Show last 5",
            ]

        # ------------------------------------------------------------------
        # DELETE
        # ------------------------------------------------------------------

        if (
            "delete" in query_lower
            or "remove" in query_lower
        ):
            return [
                "Show all leads",
                "Show all deals",
                "Show all accounts",
                "Show all contacts",
            ]

        # ------------------------------------------------------------------
        # DEFAULT
        # ------------------------------------------------------------------

        return [
            "Show all leads",
            "Show all deals",
            "Show all accounts",
            "Show all contacts",
        ]