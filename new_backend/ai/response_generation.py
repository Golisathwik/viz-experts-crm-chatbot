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
        if query.lower().startswith("search"):

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
        query,
        module,
        records,
    ):

        return [
            f"Show {module} chart",
            f"Sort {module}",
            f"Filter {module}",
            f"Export {module}"
        ]