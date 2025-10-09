import json
import re
import dateparser
from typing import Dict, Any, Optional

import google.generativeai as genai
from .settings import settings

# ✅ Configure the Google AI client with your API key
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)


def extract_entities_with_llm(transcript: str) -> Dict[str, Any]:
    """
    Uses Google's Gemini model to perform intent classification and entity extraction.
    """

    system_prompt = """
    You are an expert NLU system for a CRM. Your task is to identify the user's intent and extract entities from their transcript.
    The possible intents are: LEAD_CREATE, VISIT_SCHEDULE, LEAD_UPDATE, UNKNOWN.
    The entities to extract are: name, phone, city, source, lead_id, visit_time, status, notes.
    - For visit_time, always convert casual dates like 'tomorrow 3 pm' to a full ISO 8601 datetime string. Assume the current date is 2025-10-08.
    - For phone numbers, normalize to a simple string of digits.
    - Status must be one of: NEW, IN_PROGRESS, FOLLOW_UP, WON, LOST.
    Respond ONLY with a single, raw, minified JSON object in the format: {"intent": "...", "entities": {...}}.
    Do not wrap the JSON in markdown backticks or any other text.
    If the intent is unclear, return {"intent": "UNKNOWN", "entities": {}}.
    """

    try:
        
        model = genai.GenerativeModel(
            "gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )

        full_prompt = f"{system_prompt}\n\nTranscript: \"{transcript}\""
        response = model.generate_content(full_prompt)

        # ✅ Ensure clean text
        response_text = response.text.strip()

        # ✅ Safer JSON extraction — handles if Gemini adds extra explanation
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            raise ValueError(f"Model response not JSON: {response_text}")
        
        parsed_response = json.loads(json_match.group(0))

        # ✅ Post-process entities
        entities = parsed_response.get("entities", {})
        if "visit_time" in entities and entities["visit_time"]:
            dt = dateparser.parse(entities["visit_time"])
            if dt:
                entities["visit_time"] = dt.isoformat()

        parsed_response["entities"] = entities
        return parsed_response

    except Exception as e:
        print(f"An unexpected error occurred in NLU: {e}")
        return {"intent": "PARSING_ERROR", "entities": {}}


def validate_entities(entities: Dict[str, Any], intent: str) -> Optional[str]:
    """
    Validates that all required entities for an intent are present.
    """
    required_map = {
        "LEAD_CREATE": ["name", "phone", "city"],
        "VISIT_SCHEDULE": ["lead_id", "visit_time"],
        "LEAD_UPDATE": ["lead_id", "status"],
    }

    required = required_map.get(intent, [])
    missing = [key for key in required if key not in entities or not entities[key]]

    if missing:
        return f"Missing required entities: {', '.join(missing)}. Please provide all necessary information."

    return None
