import httpx
from .settings import settings
from .models import CrmLeadCreatePayload, CrmVisitCreatePayload, CrmLeadUpdatePayload

class CrmClient:
    """
    A client for interacting with the mock CRM API.
    It uses httpx for making synchronous HTTP requests.
    """
    def __init__(self, base_url: str):
        self.base_url = base_url
        # Set a default timeout to prevent requests from hanging indefinitely
        self.client = httpx.Client(timeout=5.0)

    def create_lead(self, payload: CrmLeadCreatePayload) -> httpx.Response:
        """Sends a request to create a new lead in the CRM."""
        url = f"{self.base_url}/crm/leads"
        # Use .model_dump() instead of .dict() for Pydantic V2 compatibility
        return self.client.post(url, json=payload.model_dump())

    def schedule_visit(self, payload: CrmVisitCreatePayload) -> httpx.Response:
        """Sends a request to schedule a visit for a lead."""
        url = f"{self.base_url}/crm/visits"
        return self.client.post(url, json=payload.model_dump())

    def update_lead_status(self, lead_id: str, payload: CrmLeadUpdatePayload) -> httpx.Response:
        """Sends a request to update the status of an existing lead."""
        url = f"{self.base_url}/crm/leads/{lead_id}/status"
        # Use .model_dump(exclude_none=True) to avoid sending optional fields that are None
        return self.client.post(url, json=payload.model_dump(exclude_none=True))

# Create a single, importable instance of the client
crm_client = CrmClient(base_url=settings.CRM_BASE_URL)