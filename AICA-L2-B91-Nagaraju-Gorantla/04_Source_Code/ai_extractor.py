import os
from typing import List, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class AICharge(BaseModel):
    description: str = Field(description="Type of additional customer charge.")
    amount_usd: float = Field(description="Positive charge amount in USD.")
    confidence: int = Field(ge=0, le=100, description="Confidence from 0 to 100.")

class AIExtractionResult(BaseModel):
    file_reference: Optional[str] = None
    containers: List[str] = Field(default_factory=list)
    charges: List[AICharge] = Field(default_factory=list)
    overall_confidence: int = Field(ge=0, le=100)
    needs_review: bool
    review_reason: Optional[str] = None

def extract_email_with_ai(email_text):
    if not email_text or not email_text.strip():
        raise ValueError("Email text is empty.")
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    client = genai.Client()
    prompt = f'''You are an accounting and logistics document extraction assistant.
Extract invoice-extra information from the email below.
IMPORTANT RULES:
1. Extract the file reference if present. Typical format: SIM-0706-26 or SIM-0706-2026.
2. Extract all valid container numbers. Typical format: four letters followed by seven digits.
3. Extract ONLY customer additional charges.
4. Ignore amounts equal to zero.
5. Do not invent any amount.
6. If quoted historical email text appears, prefer the latest/current message.
7. Do not count a written TOTAL as a separate charge if individual charges are already listed.
8. Standardize obvious spelling variations: FERRI -> FERRY; DEMURAGE -> DEMURRAGE.
9. If the email is ambiguous, incomplete, approximate, conflicting, or the relationship between charges and containers is uncertain, set needs_review = true.
10. Confidence must reflect actual certainty. Do not automatically assign 100.
EMAIL:\n------------------------------\n{email_text}\n------------------------------'''
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AIExtractionResult,
            temperature=0.1,
        ),
    )
    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")
    result = AIExtractionResult.model_validate_json(response.text)
    result.charges = [c for c in result.charges if c.amount_usd > 0]
    return result
