import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
PYTHONANYWHERE_PROXY = "http://proxy.server:3128"
from new_backend.config.settings import settings
from new_backend.repositories.zoho_oauth_repository import (
    ZohoOAuthRepository,
)

logger = logging.getLogger(__name__)

class ZohoCRMClient:
    def __init__(
        self,
        api_key: str = None,
        user_id: int = None
    ):
        self.api_key = api_key
        self.user_id = user_id
                
    def _get_zoho_connection(self) -> dict:
        """
        Get the logged-in employee's Zoho OAuth connection.
        """
        if not self.user_id:
            raise Exception(
                "Zoho user context is missing."
            )

        connection = (
            ZohoOAuthRepository.get_connection(
                self.user_id
            )
        )

        if not connection:
            raise Exception(
                "Zoho CRM is not connected for this user."
            )

        if not connection.get("refresh_token"):
            raise Exception(
                "Zoho CRM refresh token is missing. "
                "Please reconnect Zoho CRM."
            )

        return connection

    def _refresh_access_token(
        self,
        connection: dict,
    ) -> dict:
        """
        Refresh the employee's Zoho access token.
        """

        data = {
            "refresh_token": connection["refresh_token"],
            "client_id": connection["client_id"],
            "client_secret": connection["client_secret"],
            "grant_type": "refresh_token",
        }

        try:
            with httpx.Client(
                timeout=20.0,
                proxy=PYTHONANYWHERE_PROXY,
            ) as client:

                response = client.post(
                    f"{settings.ZOHO_ACCOUNTS_URL}/oauth/v2/token",
                    data=data,
                )

        except httpx.TimeoutException:
            raise Exception(
                "Zoho token refresh timed out."
            )

        except httpx.RequestError as exc:
            raise Exception(
                f"Unable to connect to Zoho authentication service: {exc}"
            )

        if response.status_code != 200:
            raise Exception(
                "Zoho access token refresh failed: "
                f"{response.text}"
            )

        result = response.json()

        access_token = result.get(
            "access_token"
        )

        if not access_token:
            raise Exception(
                "Zoho did not return a new access token."
            )

        expires_in = int(
            result.get(
                "expires_in",
                3600
            )
        )

        api_domain = (
            result.get("api_domain")
            or connection.get("api_domain")
        )

        token_expires_at = (
            datetime.now(timezone.utc)
            + timedelta(seconds=expires_in)
        ).isoformat()

        ZohoOAuthRepository.update_tokens(
            user_id=self.user_id,
            access_token=access_token,
            refresh_token=connection["refresh_token"],
            api_domain=api_domain,
            token_expires_at=token_expires_at,
        )

        connection["access_token"] = access_token
        connection["api_domain"] = api_domain
        connection["token_expires_at"] = (
            token_expires_at
        )

        return connection

    def _get_valid_zoho_connection(self) -> dict:
        """
        Return a connection with a valid access token.
        Refresh it automatically when it is expired
        or about to expire.
        """

        connection = self._get_zoho_connection()

        access_token = connection.get(
            "access_token"
        )

        expires_at = connection.get(
            "token_expires_at"
        )

        needs_refresh = not access_token

        if expires_at:

            try:
                expiry = datetime.fromisoformat(
                    expires_at
                )

                if expiry.tzinfo is None:
                    expiry = expiry.replace(
                        tzinfo=timezone.utc
                    )

                # Refresh one minute early.
                if (
                    datetime.now(timezone.utc)
                    >= expiry - timedelta(minutes=1)
                ):
                    needs_refresh = True

            except (ValueError, TypeError):
                needs_refresh = True

        else:
            needs_refresh = True

        if needs_refresh:
            connection = (
                self._refresh_access_token(
                    connection
                )
            )

        if not connection.get("api_domain"):
            raise Exception(
                "Zoho API domain is missing. "
                "Please reconnect Zoho CRM."
            )

        return connection

    def _zoho_get(
        self,
        path: str,
        params: dict | None = None,
    ) -> dict:

        connection = (
            self._get_valid_zoho_connection()
        )

        url = (
            connection["api_domain"].rstrip("/")
            + "/crm/v2/"
            + path.lstrip("/")
        )

        headers = {
            "Authorization": (
                "Zoho-oauthtoken "
                + connection["access_token"]
            ),
            "Content-Type": "application/json",
        }

        try:

            with httpx.Client(
                timeout=20.0,
                proxy=PYTHONANYWHERE_PROXY,
            ) as client:

                response = client.get(
                    url,
                    headers=headers,
                    params=params or {},
                )

        except httpx.TimeoutException:
            raise Exception(
                "Zoho CRM request timed out."
            )

        except httpx.RequestError as exc:
            raise Exception(
                f"Unable to connect to Zoho CRM: {exc}"
            )

        # Access token may have expired between our
        # expiry check and the actual request.
        if response.status_code == 401:

            connection = (
                self._refresh_access_token(
                    connection
                )
            )

            headers["Authorization"] = (
                "Zoho-oauthtoken "
                + connection["access_token"]
            )

            with httpx.Client(
                timeout=20.0,
                proxy=PYTHONANYWHERE_PROXY,
            ) as client:

                response = client.get(
                    url,
                    headers=headers,
                    params=params or {},
                )

        if response.status_code == 204:
            return {}

        try:
            result = response.json()
        except Exception:
            result = {}

        if response.status_code >= 400:

            error_message = (
                result.get("message")
                or result.get("code")
                or response.text
                or "Zoho CRM request failed."
            )

            raise Exception(
                f"Zoho CRM API error "
                f"(HTTP {response.status_code}): "
                f"{error_message}"
            )

        return result

    def _zoho_put(
        self,
        path: str,
        data: dict,
    ) -> dict:

        connection = (
            self._get_valid_zoho_connection()
        )

        url = (
            connection["api_domain"].rstrip("/")
            + "/crm/v2/"
            + path.lstrip("/")
        )

        headers = {
            "Authorization": (
                "Zoho-oauthtoken "
                + connection["access_token"]
            ),
            "Content-Type": "application/json",
        }

        try:

            with httpx.Client(
                timeout=20.0,
                proxy=PYTHONANYWHERE_PROXY,
            ) as client:

                response = client.put(
                    url,
                    headers=headers,
                    json=data,
                )

        except httpx.TimeoutException:
            raise Exception(
                "Zoho CRM request timed out."
            )

        except httpx.RequestError as exc:
            raise Exception(
                f"Unable to connect to Zoho CRM: {exc}"
            )

        # Access token may have expired between our
        # expiry check and the actual request.
        if response.status_code == 401:

            connection = (
                self._refresh_access_token(
                    connection
                )
            )

            headers["Authorization"] = (
                "Zoho-oauthtoken "
                + connection["access_token"]
            )

            with httpx.Client(
                timeout=20.0,
                proxy=PYTHONANYWHERE_PROXY,
            ) as client:

                response = client.put(
                    url,
                    headers=headers,
                    json=data,
                )

        if response.status_code == 204:
            return {}

        try:
            result = response.json()
        except Exception:
            result = {}

        if response.status_code >= 400:

            error_message = (
                result.get("message")
                or result.get("code")
                or response.text
                or "Zoho CRM request failed."
            )

            raise Exception(
                f"Zoho CRM API error "
                f"(HTTP {response.status_code}): "
                f"{error_message}"
            )

        return result
    
    def _zoho_delete(
        self,
        path: str,
    ) -> dict:

        connection = (
            self._get_valid_zoho_connection()
        )

        url = (
            connection["api_domain"].rstrip("/")
            + "/crm/v2/"
            + path.lstrip("/")
        )

        headers = {
            "Authorization": (
                "Zoho-oauthtoken "
                + connection["access_token"]
            ),
            "Content-Type": "application/json",
        }

        try:

            with httpx.Client(
                timeout=20.0,
                proxy=PYTHONANYWHERE_PROXY,
            ) as client:

                response = client.delete(
                    url,
                    headers=headers,
                )

        except httpx.TimeoutException:
            raise Exception(
                "Zoho CRM request timed out."
            )

        except httpx.RequestError as exc:
            raise Exception(
                f"Unable to connect to Zoho CRM: {exc}"
            )

        # Access token may have expired between our
        # expiry check and the actual request.
        if response.status_code == 401:

            connection = (
                self._refresh_access_token(
                    connection
                )
            )

            headers["Authorization"] = (
                "Zoho-oauthtoken "
                + connection["access_token"]
            )

            with httpx.Client(
                timeout=20.0,
                proxy=PYTHONANYWHERE_PROXY,
            ) as client:

                response = client.delete(
                    url,
                    headers=headers,
                )

        if response.status_code == 204:
            return {}

        try:
            result = response.json()
        except Exception:
            result = {}

        if response.status_code >= 400:

            error_message = (
                result.get("message")
                or result.get("code")
                or response.text
                or "Zoho CRM delete request failed."
            )

            raise Exception(
                f"Zoho CRM API error "
                f"(HTTP {response.status_code}): "
                f"{error_message}"
            )

        return result
    
    def _zoho_post(
        self,
        path: str,
        data: dict,
    ) -> dict:

        connection = (
            self._get_valid_zoho_connection()
        )

        url = (
            connection["api_domain"].rstrip("/")
            + "/crm/v2/"
            + path.lstrip("/")
        )

        headers = {
            "Authorization": (
                "Zoho-oauthtoken "
                + connection["access_token"]
            ),
            "Content-Type": "application/json",
        }

        try:

            with httpx.Client(
                timeout=20.0,
                proxy=PYTHONANYWHERE_PROXY,
            ) as client:

                response = client.post(
                    url,
                    headers=headers,
                    json=data,
                )

        except httpx.TimeoutException:
            raise Exception(
                "Zoho CRM request timed out."
            )

        except httpx.RequestError as exc:
            raise Exception(
                f"Unable to connect to Zoho CRM: {exc}"
            )

        # Access token may have expired between our
        # expiry check and the actual request.
        if response.status_code == 401:

            connection = (
                self._refresh_access_token(
                    connection
                )
            )

            headers["Authorization"] = (
                "Zoho-oauthtoken "
                + connection["access_token"]
            )

            with httpx.Client(
                timeout=20.0,
                proxy=PYTHONANYWHERE_PROXY,
            ) as client:

                response = client.post(
                    url,
                    headers=headers,
                    json=data,
                )

        if response.status_code == 204:
            return {}

        try:
            result = response.json()
        except Exception:
            result = {}

        if response.status_code >= 400:

            error_message = (
                result.get("message")
                or result.get("code")
                or response.text
                or "Zoho CRM create request failed."
            )

            raise Exception(
                f"Zoho CRM API error "
                f"(HTTP {response.status_code}): "
                f"{error_message}"
            )

        return result
    
    def test_connection(self) -> bool:
        """
        Tests the direct Zoho CRM OAuth connection.
        """

        try:
            # This endpoint verifies that the stored
            # OAuth access token can successfully access
            # the Zoho CRM organization.
            result = self._zoho_get("org")

            if isinstance(result, dict):
                return bool(
                    result.get("org")
                )

            return False

        except Exception as exc:
            logger.warning(
                "Zoho CRM connection test failed: %s",
                exc
            )
            return False

    def _extract_list(self, result, key: str) -> list:
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            if key in result:
                return result[key]
            if "data" in result:
                return result["data"]
            for val in result.values():
                if isinstance(val, list):
                    return val
            return [result]
        return []

    def get_leads(
        self,
        query: str = None
    ) -> list:
        """
        Get Leads directly from Zoho CRM.

        Preserves the old n8n behavior:

        No query:
            GET /crm/v2/Leads
            per_page=200

        Query:
            GET /crm/v2/Leads/search?word=<query>
        """

        query = (
            query.strip()
            if isinstance(query, str)
            else query
        )

        # --------------------------------------------------
        # SEARCH LEADS
        # Same route previously used by n8n.
        # --------------------------------------------------

        if query:

            result = self._zoho_get(
                "Leads/search",
                params={
                    "word": query
                },
            )

            data = result.get(
                "data",
                []
            )

            if not isinstance(data, list):
                return []

            return data

        # --------------------------------------------------
        # GET ALL LEADS
        # Same n8n behavior: maximum 200 records.
        # --------------------------------------------------

        result = self._zoho_get(
            "Leads",
            params={
                "per_page": 200
            },
        )

        data = result.get(
            "data",
            []
        )

        if not isinstance(data, list):
            return []

        return data

    def get_contacts(
        self,
        query: str = None
    ) -> list:
        """
        Get Contacts directly from Zoho CRM.

        Preserves the old n8n behavior:

        No query:
            GET /crm/v2/Contacts
            per_page=200

        Email query:
            GET /crm/v2/Contacts/search?email=<email>

        Other query:
            GET /crm/v2/Contacts/search?word=<query>
        """

        query = (
            query.strip()
            if isinstance(query, str)
            else query
        )

        # --------------------------------------------------
        # SEARCH CONTACTS
        # --------------------------------------------------

        if query:

            # Same behavior as n8n:
            # email address -> email search
            if "@" in query:

                result = self._zoho_get(
                    "Contacts/search",
                    params={
                        "email": query
                    },
                )

            else:

                result = self._zoho_get(
                    "Contacts/search",
                    params={
                        "word": query
                    },
                )

            data = result.get(
                "data",
                []
            )

            if not isinstance(data, list):
                return []

            return data

        # --------------------------------------------------
        # GET ALL CONTACTS
        # --------------------------------------------------

        result = self._zoho_get(
            "Contacts",
            params={
                "per_page": 200
            },
        )

        data = result.get(
            "data",
            []
        )

        if not isinstance(data, list):
            return []

        return data

    def get_deals(
        self,
        query: str = None,
        open_only: bool = False
    ) -> list:
        """
        Get Deals directly from Zoho CRM.

        Preserves the old n8n behavior:

        No query:
            GET /crm/v2/Deals
            per_page=200

        Query:
            GET /crm/v2/Deals/search?word=<query>

        open_only=True:
            Excludes Closed Won and Closed Lost deals.
        """

        query = (
            query.strip()
            if isinstance(query, str)
            else query
        )

        # --------------------------------------------------
        # SEARCH DEALS
        # --------------------------------------------------

        if query:

            result = self._zoho_get(
                "Deals/search",
                params={
                    "word": query
                },
            )

        # --------------------------------------------------
        # GET ALL DEALS
        # --------------------------------------------------

        else:

            result = self._zoho_get(
                "Deals",
                params={
                    "per_page": 200
                },
            )

        data = result.get(
            "data",
            []
        )

        if not isinstance(data, list):
            return []

        # --------------------------------------------------
        # OPEN DEALS ONLY
        # --------------------------------------------------

        if open_only:

            data = [
                deal
                for deal in data
                if isinstance(deal, dict)
                and deal.get("Stage")
                not in [
                    "Closed Won",
                    "Closed Lost"
                ]
            ]

        return data

    def get_accounts(
        self,
        query: str = None
    ) -> list:
        """
        Get Accounts directly from Zoho CRM.

        Preserves the old n8n behavior:

        No query:
            GET /crm/v2/Accounts
            per_page=200

        Query:
            GET /crm/v2/Accounts/search?word=<query>
        """

        query = (
            query.strip()
            if isinstance(query, str)
            else query
        )

        # --------------------------------------------------
        # SEARCH ACCOUNTS
        # --------------------------------------------------

        if query:

            result = self._zoho_get(
                "Accounts/search",
                params={
                    "word": query
                },
            )

            data = result.get(
                "data",
                []
            )

            if not isinstance(data, list):
                return []

            return data

        # --------------------------------------------------
        # GET ALL ACCOUNTS
        # --------------------------------------------------

        result = self._zoho_get(
            "Accounts",
            params={
                "per_page": 200
            },
        )

        data = result.get(
            "data",
            []
        )

        if not isinstance(data, list):
            return []

        return data

    def get_activities(self) -> list:
        """
        Get CRM activities directly from Zoho CRM.

        Preserves the existing interface:
            get_activities() -> list
        """

        result = self._zoho_get(
            "Activities",
            params={
                "per_page": 200
            },
        )

        return self._extract_list(
            result,
            "activities"
        )

    def search_lead_by_name(self, name: str) -> list:
        return self.get_leads(query=name)

    def search_contact_by_email(self, email: str) -> list:
        return self.get_contacts(query=email)

    def get_deal_status(self, deal_name: str) -> dict:
        deals = self.get_deals(query=deal_name)
        if deals:
            if isinstance(deals, list):
                return deals[0]
            elif isinstance(deals, dict):
                return deals
        return {}

    def get_pipeline_summary(self) -> dict:
        """
        Build the CRM pipeline summary directly from Zoho Deals.

        Preserves the existing behavior:
            - Uses the same Deals source as get_deals()
            - Groups deal values by Stage
            - Calculates total_value across all deals
            - Calculates active_value excluding Closed Won/Closed Lost
            - Calculates deal_count
            - Returns the same response structure
        """

        try:
            # --------------------------------------------------
            # Get the same Deals data used by the existing
            # direct Zoho implementation.
            #
            # get_deals() without a query:
            # GET /crm/v2/Deals
            # per_page=200
            # --------------------------------------------------

            deals = self.get_deals()

            if not isinstance(deals, list):
                deals = []

            # --------------------------------------------------
            # Build pipeline summary
            # --------------------------------------------------

            summary = {}
            total_value = 0.0
            active_value = 0.0

            for deal in deals:

                if not isinstance(deal, dict):
                    continue

                # Zoho CRM uses "Stage".
                # Keep lowercase fallback for compatibility
                # with any previously normalized data.
                stage = (
                    deal.get("Stage")
                    if deal.get("Stage") is not None
                    else deal.get("stage", "")
                )

                # Zoho CRM uses "Amount".
                # Keep lowercase fallback for compatibility.
                amount_value = (
                    deal.get("Amount")
                    if deal.get("Amount") is not None
                    else deal.get("amount")
                )

                # Preserve previous behavior:
                # None / empty amount becomes 0.
                amount = float(amount_value or 0)

                # Preserve grouping by stage.
                summary[stage] = (
                    summary.get(stage, 0.0) + amount
                )

                # Total includes ALL deals.
                total_value += amount

                # Active excludes Closed Won and Closed Lost.
                if stage not in [
                    "Closed Won",
                    "Closed Lost"
                ]:
                    active_value += amount

            # --------------------------------------------------
            # Preserve the exact existing response structure.
            # --------------------------------------------------

            return {
                "by_stage": summary,
                "total_value": total_value,
                "active_value": active_value,
                "deal_count": len(deals)
            }

        except Exception as e:
            raise e

    def get_crm_statistics(self) -> dict:
        """
        Build CRM statistics directly from Zoho CRM.

        Preserves the existing return type:
            dict

        Uses the same CRM modules already supported
        by the application.
        """

        try:
            leads = self.get_leads()
            contacts = self.get_contacts()
            accounts = self.get_accounts()
            deals = self.get_deals()

            # ----------------------------------------------
            # Basic totals
            # ----------------------------------------------

            total_leads = len(leads)
            total_contacts = len(contacts)
            total_accounts = len(accounts)
            total_deals = len(deals)

            # ----------------------------------------------
            # Lead status distribution
            # ----------------------------------------------

            lead_status = {}

            for record in leads:

                if not isinstance(record, dict):
                    continue

                status = (
                    record.get("Lead_Status")
                    or record.get("Status")
                    or "Unknown"
                )

                lead_status[status] = (
                    lead_status.get(status, 0) + 1
                )

            # ----------------------------------------------
            # Deal stage distribution
            # ----------------------------------------------

            deal_stages = {}
            total_revenue = 0.0

            for record in deals:

                if not isinstance(record, dict):
                    continue

                stage = (
                    record.get("Stage")
                    or "Unknown"
                )

                deal_stages[stage] = (
                    deal_stages.get(stage, 0) + 1
                )

                amount = record.get("Amount") or 0

                try:
                    if isinstance(amount, str):
                        amount = (
                            amount
                            .replace(",", "")
                            .replace("₹", "")
                            .strip()
                        )

                    total_revenue += float(amount)

                except (
                    TypeError,
                    ValueError
                ):
                    pass

            # ----------------------------------------------
            # Contact source distribution
            # ----------------------------------------------

            contact_sources = {}

            for record in contacts:

                if not isinstance(record, dict):
                    continue

                source = (
                    record.get("Lead_Source")
                    or "Unknown"
                )

                contact_sources[source] = (
                    contact_sources.get(source, 0) + 1
                )

            # ----------------------------------------------
            # Account industry distribution
            # ----------------------------------------------

            account_industries = {}

            for record in accounts:

                if not isinstance(record, dict):
                    continue

                industry = record.get("Industry")

                if industry:
                    account_industries[industry] = (
                        account_industries.get(
                            industry,
                            0
                        ) + 1
                    )

            # ----------------------------------------------
            # Preserve CRM statistics as a dictionary.
            # ----------------------------------------------

            return {
                "total_leads": total_leads,
                "total_contacts": total_contacts,
                "total_accounts": total_accounts,
                "total_deals": total_deals,

                "lead_status_distribution": lead_status,

                "deal_stage_distribution": deal_stages,

                "total_revenue": total_revenue,

                "contact_source_distribution": contact_sources,

                "account_industry_distribution": (
                    account_industries
                ),
            }

        except Exception as e:
            raise e

    def get_record_by_id(
        self,
        module: str,
        record_id: str
    ) -> dict:
        """
        Get one complete CRM record directly from Zoho CRM.

        Preserves the existing interface used by the backend:
            get_record_by_id(module, record_id) -> dict

        Supported modules:
            Leads
            Contacts
            Accounts
            Deals
        """

        module = (
            module.strip()
            if isinstance(module, str)
            else module
        )

        record_id = (
            str(record_id).strip()
            if record_id is not None
            else ""
        )

        if not module:
            raise Exception(
                "CRM module is required."
            )

        if not record_id:
            raise Exception(
                "CRM record ID is required."
            )

        # --------------------------------------------------
        # Normalize module name
        # --------------------------------------------------

        module_map = {
            "Lead": "Leads",
            "Leads": "Leads",

            "Contact": "Contacts",
            "Contacts": "Contacts",

            "Account": "Accounts",
            "Accounts": "Accounts",

            "Deal": "Deals",
            "Deals": "Deals",
        }

        zoho_module = module_map.get(module)

        if not zoho_module:
            raise Exception(
                f"Unsupported CRM module: {module}"
            )

        # --------------------------------------------------
        # Get the complete record directly from Zoho.
        #
        # Equivalent to the four n8n Zoho "Get" branches.
        # --------------------------------------------------

        result = self._zoho_get(
            f"{zoho_module}/{record_id}"
        )

        # Zoho returns:
        #
        # {
        #     "data": [
        #         {
        #             ...
        #         }
        #     ]
        # }
        #
        # The old method returned the first record itself,
        # not the outer "data" wrapper.
        # Preserve that exact contract.
        data = result.get(
            "data",
            []
        )

        if isinstance(data, list) and data:
            record = data[0]

            if isinstance(record, dict):
                return record

        return {}

    def update_record(
        self,
        module: str,
        record_id: str,
        field_name: str,
        value: str
    ) -> bool:

        # --------------------------------------------------
        # Same validation performed by n8n
        # --------------------------------------------------

        if not module:
            raise Exception(
                "Missing module"
            )

        if not record_id:
            raise Exception(
                "Missing record id"
            )

        if not field_name:
            raise Exception(
                "Missing field name"
            )

        if value is None:
            raise Exception(
                "Missing value"
            )

        # --------------------------------------------------
        # Same module routing used by the n8n Switch.
        # --------------------------------------------------

        allowed_modules = {
            "Leads",
            "Contacts",
            "Accounts",
            "Deals",
        }

        if module not in allowed_modules:
            raise Exception(
                f"Unsupported CRM module: {module}"
            )

        # --------------------------------------------------
        # Same payload created by:
        #
        # Prepare Zoho Update Payload
        #
        # {
        #     "data": [
        #         {
        #             field_name: value
        #         }
        #     ]
        # }
        # --------------------------------------------------

        api_payload = {
            "data": [
                {
                    field_name: value
                }
            ]
        }

        # --------------------------------------------------
        # Same final URL constructed by n8n
        # --------------------------------------------------

        final_path = (
            f"{module}/{record_id}"
        )

        # --------------------------------------------------
        # Same PUT operation performed by n8n
        # --------------------------------------------------

        put_response = self._zoho_put(
            final_path,
            api_payload
        )

        # --------------------------------------------------
        # Same validation as "Check Update Success"
        #
        # n8n considers:
        # status = "success"
        # OR
        # code   = "SUCCESS"
        #
        # as successful.
        # --------------------------------------------------

        data_array = (
            put_response.get("data")
            if isinstance(
                put_response,
                dict
            )
            else None
        )

        if (
            not isinstance(data_array, list)
            or not data_array
        ):
            return False

        record_result = data_array[0]

        if not isinstance(
            record_result,
            dict
        ):
            return False

        if (
            record_result.get("status")
            != "success"
            and
            record_result.get("code")
            != "SUCCESS"
        ):
            return False

        # --------------------------------------------------
        # IMPORTANT:
        #
        # n8n then performs:
        #
        # GET /crm/v2/{module}/{id}
        #
        # to obtain the fresh updated record.
        #
        # We MUST keep this behavior even though the
        # current FastAPI interface returns only bool.
        # --------------------------------------------------

        try:

            fresh_record_response = (
                self._zoho_get(
                    final_path
                )
            )

            fresh_data = (
                fresh_record_response.get(
                    "data",
                    []
                )
                if isinstance(
                    fresh_record_response,
                    dict
                )
                else []
            )

            fresh_record = (
                fresh_data[0]
                if isinstance(
                    fresh_data,
                    list
                ) and fresh_data
                else None
            )

            # The fresh record is intentionally retrieved
            # to preserve the n8n workflow behavior.
            #
            # The existing FastAPI interface expects bool,
            # so we do not change the return type.

        except Exception:
            # n8n returns success=true even when the
            # post-update GET fails.
            #
            # Therefore the update itself remains successful.
            fresh_record = None

        return True
    
    def create_record(
        self,
        module: str,
        fields: dict,
    ) -> dict:

        # --------------------------------------------------
        # Same validation performed by n8n
        # --------------------------------------------------

        if not module:
            raise Exception(
                "Missing module"
            )

        if not fields:
            raise Exception(
                "Missing fields"
            )

        # --------------------------------------------------
        # Same module validation/routing as n8n.
        # --------------------------------------------------

        allowed_modules = {
            "Leads",
            "Contacts",
            "Accounts",
            "Deals",
        }

        if module not in allowed_modules:
            raise Exception(
                f"Unsupported CRM module: {module}"
            )

        # --------------------------------------------------
        # Same payload created by:
        #
        # Prepare Zoho Create Payload
        #
        # {
        #     "data": [
        #         fields
        #     ]
        # }
        # --------------------------------------------------

        api_payload = {
            "data": [
                fields
            ]
        }

        # --------------------------------------------------
        # Same POST operation performed by n8n.
        # --------------------------------------------------

        create_response = self._zoho_post(
            module,
            api_payload
        )

        # --------------------------------------------------
        # Validate Zoho create response.
        #
        # n8n accepts:
        # status = "success"
        # OR
        # code   = "SUCCESS"
        # --------------------------------------------------

        data_array = (
            create_response.get("data")
            if isinstance(
                create_response,
                dict
            )
            else None
        )

        if (
            not isinstance(data_array, list)
            or not data_array
        ):
            return {
                "success": False,
                "error": (
                    create_response.get("message")
                    if isinstance(
                        create_response,
                        dict
                    )
                    else "Invalid response from Zoho CRM."
                ),
                "zoho_response": create_response,
            }

        record_result = data_array[0]

        if not isinstance(
            record_result,
            dict
        ):
            return {
                "success": False,
                "error": "Invalid response from Zoho CRM.",
                "zoho_response": create_response,
            }

        status = (
            record_result.get("status")
            or record_result.get("code")
            or ""
        )

        if str(status).upper() not in [
            "SUCCESS"
        ]:
            return {
                "success": False,
                "error": (
                    record_result.get("message")
                    or record_result.get("code")
                    or "Create failed."
                ),
                "zoho_response": create_response,
            }

        # --------------------------------------------------
        # Get newly created record ID.
        # --------------------------------------------------

        details = record_result.get(
            "details",
            {}
        )

        record_id = (
            details.get("id")
            if isinstance(details, dict)
            else None
        )

        if not record_id:
            return {
                "success": False,
                "error": (
                    "Record was created, but Zoho "
                    "did not return the record ID."
                ),
                "zoho_response": create_response,
            }

        # --------------------------------------------------
        # Same behavior as n8n:
        #
        # GET /crm/v2/{module}/{id}
        #
        # to retrieve the complete newly created record.
        # --------------------------------------------------

        created_record = None

        try:

            fresh_record_response = (
                self._zoho_get(
                    f"{module}/{record_id}"
                )
            )

            fresh_data = (
                fresh_record_response.get(
                    "data",
                    []
                )
                if isinstance(
                    fresh_record_response,
                    dict
                )
                else []
            )

            if (
                isinstance(
                    fresh_data,
                    list
                )
                and fresh_data
            ):
                if isinstance(
                    fresh_data[0],
                    dict
                ):
                    created_record = fresh_data[0]

        except Exception:
            # The creation itself succeeded.
            # Keep the create successful even if
            # retrieving the fresh record fails.
            created_record = None

        # --------------------------------------------------
        # Preserve the response structure expected
        # by the existing FastAPI create workflow.
        # --------------------------------------------------

        return {
            "success": True,
            "message": "Record created successfully.",
            "id": record_id,
            "module": module,
            "created_record": (
                created_record
                or details
            ),
            "zoho_response": create_response,
        }
        
    def delete_record(
        self,
        module: str,
        record_id: str
    ) -> bool:

        # --------------------------------------------------
        # Same validation performed by n8n
        # --------------------------------------------------

        if not module:
            raise Exception(
                "Missing module"
            )

        if not record_id:
            raise Exception(
                "Missing record id"
            )

        # --------------------------------------------------
        # Same module validation/routing as n8n.
        # --------------------------------------------------

        allowed_modules = {
            "Leads",
            "Contacts",
            "Accounts",
            "Deals",
        }

        if module not in allowed_modules:
            raise Exception(
                f"Unsupported CRM module: {module}"
            )

        # --------------------------------------------------
        # Same URL constructed by:
        #
        # Prepare Zoho Delete Payload
        #
        # https://www.zohoapis.in/crm/v2/
        # {module}/{id}
        # --------------------------------------------------

        final_path = (
            f"{module}/{record_id}"
        )

        # --------------------------------------------------
        # Same DELETE request performed by n8n.
        # --------------------------------------------------

        delete_response = self._zoho_delete(
            final_path
        )

        # --------------------------------------------------
        # Same success validation performed by
        # "Format Delete Response" in n8n.
        #
        # n8n checks:
        #
        # response.data[0].status === "success"
        # --------------------------------------------------

        data_array = (
            delete_response.get("data")
            if isinstance(
                delete_response,
                dict
            )
            else None
        )

        if (
            not isinstance(data_array, list)
            or not data_array
        ):
            return False

        record_result = data_array[0]

        if not isinstance(
            record_result,
            dict
        ):
            return False

        if (
            record_result.get("status")
            == "success"
        ):
            return True

        # Also accept Zoho's SUCCESS code,
        # matching the tolerant handling already
        # used by the migrated operations.
        if (
            str(
                record_result.get("code", "")
            ).upper()
            == "SUCCESS"
        ):
            return True

        return False
