from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# --- API Request/Response Models ---

class BotRequest(BaseModel):
    transcript: str = Field(..., max_length=1000) # Input size guard

class CrmCall(BaseModel):
    endpoint: str
    method: str
    status_code: int

class SuccessResult(BaseModel):
    message: str

class BotSuccessResponse(BaseModel):
    intent: str
    entities: Dict[str, Any]
    crm_call: CrmCall
    result: SuccessResult

class ErrorDetails(BaseModel):
    type: str
    details: str

class BotErrorResponse(BaseModel):
    intent: str
    error: ErrorDetails

# --- CRM Client Models ---

class CrmLeadCreatePayload(BaseModel):
    name: str
    phone: str
    city: str
    source: Optional[str] = None

class CrmVisitCreatePayload(BaseModel):
    lead_id: str
    visit_time: str
    notes: Optional[str] = None

class CrmLeadUpdatePayload(BaseModel):
    status: str
    notes: Optional[str] = None
