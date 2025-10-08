import pytest
from fastapi.testclient import TestClient
from httpx import Response, RequestError, Request
from bot.app import app

client = TestClient(app)

def test_lead_create_complex_query(mocker):
    """Tests the happy path for creating a lead with a complex, conversational query."""
    # Mock the LLM's response
    mock_llm_response = {
        "intent": "LEAD_CREATE",
        "entities": {
            "name": "Rohan Sharma",
            "city": "Gurgaon",
            "phone": "9876543210",
            "source": "Instagram"
        }
    }
    mocker.patch("bot.nlu.extract_entities_with_llm", return_value=mock_llm_response)

    # FIX: Create a more realistic mock response with a Request object
    mock_crm_response = Response(200, json={"lead_id": "mock-uuid-123", "status": "NEW"})
    mock_crm_response.request = Request("POST", "http://mock-crm/crm/leads")

    mocker.patch(
        "bot.crm_client.crm_client.create_lead",
        return_value=mock_crm_response
    )

    # Test the endpoint
    response = client.post(
        "/bot/handle",
        json={"transcript": "Hey, could you add a new lead for me? His name is Rohan Sharma, he's from Gurgaon. His phone is 98765 43210 and he came from Instagram."}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "LEAD_CREATE"
    assert data["result"]["message"] == "Successfully created lead with ID: mock-uuid-123"


def test_visit_schedule_casual_date(mocker):
    """Tests scheduling a visit using a casual date phrase."""
    mock_llm_response = {
        "intent": "VISIT_SCHEDULE",
        "entities": {
            "lead_id": "7b1b8f54",
            "visit_time": "2025-10-07T15:00:00" # LLM is expected to convert "tomorrow 3pm"
        }
    }
    mocker.patch("bot.nlu.extract_entities_with_llm", return_value=mock_llm_response)

    # FIX: Create a more realistic mock response with a Request object
    mock_crm_response = Response(200, json={"visit_id": "visit-uuid-456", "status": "SCHEDULED"})
    mock_crm_response.request = Request("POST", "http://mock-crm/crm/visits")
    
    mocker.patch(
        "bot.crm_client.crm_client.schedule_visit",
        return_value=mock_crm_response
    )

    response = client.post(
        "/bot/handle",
        json={"transcript": "Can you schedule a visit for lead 7b1b8f54 for tomorrow at 3 pm?"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "VISIT_SCHEDULE"
    assert data["result"]["message"] == "Successfully scheduled visit with ID: visit-uuid-456"


def test_validation_error_missing_entity(mocker):
    """Tests that a VALIDATION_ERROR is returned if required entities are missing."""
    mock_llm_response = {
        "intent": "LEAD_CREATE",
        "entities": {"name": "Rohan Sharma"} # Missing phone and city
    }
    mocker.patch("bot.nlu.extract_entities_with_llm", return_value=mock_llm_response)

    response = client.post(
        "/bot/handle",
        json={"transcript": "Add lead Rohan Sharma"}
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"]["type"] == "VALIDATION_ERROR"
    assert "Missing required entities: phone, city" in data["error"]["details"]


def test_crm_500_error(mocker):
    """Tests that a CRM_ERROR is returned if the CRM call fails."""
    mock_llm_response = {
        "intent": "LEAD_CREATE",
        "entities": {"name": "Test User", "phone": "1234567890", "city": "Testville"}
    }
    mocker.patch("bot.nlu.extract_entities_with_llm", return_value=mock_llm_response)
    
    # Mock the CRM client to raise a connection error
    mocker.patch(
        "bot.crm_client.crm_client.create_lead",
        side_effect=RequestError("Connection failed")
    )

    response = client.post(
        "/bot/handle",
        json={"transcript": "Create lead Test User phone 1234567890 from Testville"}
    )

    assert response.status_code == 503
    data = response.json()
    assert data["error"]["type"] == "CRM_ERROR"