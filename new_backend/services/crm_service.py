from new_backend.crm.zoho_client import ZohoCRMClient


class CRMService:
    
    def __init__(
        self,
        api_key: str = None,
        user_id: int = None
    ):
        self.client = ZohoCRMClient(
            api_key=api_key,
            user_id=user_id
        )

    def test_connection(self):
        return self.client.test_connection()

    def get_leads(self, query=None):
        return self.client.get_leads(query)

    def get_contacts(self, query=None):
        return self.client.get_contacts(query)

    def get_accounts(self, query=None):
        return self.client.get_accounts(query)

    def get_deals(self, query=None, open_only=False):
        return self.client.get_deals(query, open_only)

    def get_record_by_id(self, module, record_id):
        return self.client.get_record_by_id(module, record_id)

    def update_record(
        self,
        module,
        record_id,
        field_name,
        value
    ):
        return self.client.update_record(
            module,
            record_id,
            field_name,
            value
        )
        
    def delete_record(
        self,
        module,
        record_id
    ):
        return self.client.delete_record(
            module,
            record_id
        )
    
    def create_record(
        self,
        module,
        fields,
    ):
        return self.client.create_record(
            module,
            fields,
        )

    def get_pipeline_summary(self):
        return self.client.get_pipeline_summary()

    def get_crm_statistics(self):
        return self.client.get_crm_statistics()