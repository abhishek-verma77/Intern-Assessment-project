import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import RequestError
from . import nlu
from .crm_client import crm_client
from .models import (
    BotRequest, BotSuccessResponse, BotErrorResponse, ErrorDetails, CrmCall, SuccessResult,
    CrmLeadCreatePayload, CrmVisitCreatePayload, CrmLeadUpdatePayload
)
from .settings import settings

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL.upper())
logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/bot/handle", response_model=None)
async def handle_bot_request(req: BotRequest):
    transcript = req.transcript
    logger.info(f"Received transcript: '{transcript}'")

    nlu_result = nlu.extract_entities_with_llm(transcript)
    intent = nlu_result.get("intent", "UNKNOWN")
    entities = nlu_result.get("entities", {})

    logger.info(f"NLU result - Intent: {intent}, Entities: {entities}")
    
    if intent in ["UNKNOWN", "PARSING_ERROR"]:
        error = ErrorDetails(type="PARSING_ERROR", details="Could not understand the request.")
        return JSONResponse(status_code=400, content=BotErrorResponse(intent=intent, error=error).model_dump())
    
    validation_error = nlu.validate_entities(entities, intent)
    if validation_error:
        error = ErrorDetails(type="VALIDATION_ERROR", details=validation_error)
        return JSONResponse(status_code=400, content=BotErrorResponse(intent=intent, error=error).model_dump())

    try:
        response = None # Initialize response to handle cases where intent doesn't match
        if intent == "LEAD_CREATE":
            payload = CrmLeadCreatePayload(**entities)
            response = crm_client.create_lead(payload)
            message = f"Successfully created lead with ID: {response.json().get('lead_id')}"
        
        elif intent == "VISIT_SCHEDULE":
            payload = CrmVisitCreatePayload(**entities)
            response = crm_client.schedule_visit(payload)
            message = f"Successfully scheduled visit with ID: {response.json().get('visit_id')}"
            
        elif intent == "LEAD_UPDATE":
            lead_id = entities.pop("lead_id")
            payload = CrmLeadUpdatePayload(**entities)
            response = crm_client.update_lead_status(lead_id, payload)
            message = f"Successfully updated lead {lead_id} to status {response.json().get('status')}"
        
        if response:
            response.raise_for_status()
            
            logger.info(f"CRM call successful. Endpoint: {response.request.url}, Status: {response.status_code}, Response: {response.text}")
            
            crm_call = CrmCall(
                endpoint=str(response.request.url),
                method=response.request.method,
                status_code=response.status_code
            )
            result = SuccessResult(message=message)
            bot_response = BotSuccessResponse(intent=intent, entities=entities, crm_call=crm_call, result=result)
            
            return JSONResponse(status_code=200, content=bot_response.model_dump())
        else:
             # This case would only be hit if the intent is recognized but not one of the three above
             error = ErrorDetails(type="PARSING_ERROR", details="Intent recognized but no action configured.")
             return JSONResponse(status_code=500, content=BotErrorResponse(intent=intent, error=error).model_dump())


    except RequestError as e:
        logger.error(f"CRM connection error: {e}")
        error = ErrorDetails(type="CRM_ERROR", details=f"CRM connection error: {e}")
        return JSONResponse(status_code=503, content=BotErrorResponse(intent=intent, error=error).model_dump())
    except Exception as e:
        logger.error(f"An unexpected internal error occurred: {e}", exc_info=True)
        if hasattr(e, 'response') and e.response is not None:
             error_detail = e.response.text
             logger.error(f"CRM returned non-2xx response: {error_detail}")
             error = ErrorDetails(type="CRM_ERROR", details=f"CRM returned an error: {error_detail}")
             return JSONResponse(status_code=502, content=BotErrorResponse(intent=intent, error=error).model_dump())
        else:
             error = ErrorDetails(type="PARSING_ERROR", details=f"An internal error occurred: {str(e)}")
             return JSONResponse(status_code=500, content=BotErrorResponse(intent=intent, error=error).model_dump())

