"""
Agent 1 — Client Onboarding Agent.

perceive -> reason -> act -> validate loop that turns a photo/PDF of a PAN card
or GST certificate into a Client Master row matching the L1 app's schema.
See prompts/onboarding_agent.md for the prompt and design rationale.
"""
import base64
import io
import json
import os
import sys
from pathlib import Path

import anthropic
import pdfplumber
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schema import normalize_entity_type, validate_client_row, GSTIN_STATE_CODES

load_dotenv()

MODEL = "claude-sonnet-5"
MIN_TEXT_LAYER_CHARS = 40  # below this, treat a PDF page as scanned/image-only

SYSTEM_PROMPT = """You are a data-extraction assistant for an Indian chartered \
accountancy firm's client onboarding workflow. You will be shown a PAN card or a \
GST registration certificate (as an image, or as text extracted from a PDF/OCR). \
Extract the following fields and return ONLY a JSON object with these exact keys \
— no prose, no markdown fences:

{
  "name": string,
  "entity": string,
  "pan": string,
  "gstin": string,
  "cin": string,
  "contact": string,
  "mobile": string,
  "email": string,
  "address": string,
  "state": string,
  "sez": boolean
}

entity must be one of: Individual, Proprietorship, Partnership, LLP, Private \
Limited Company, Public Limited Company, Trust, Society, Other. Infer it from \
"Constitution of Business" on a GST certificate, or default to "Individual" for \
a bare PAN card.

If a field is not present on the document, use an empty string ("") rather than \
guessing or hallucinating a value. Never fabricate a PAN or GSTIN."""

IMAGE_EXTENSIONS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


class OnboardingAgent:
    def __init__(self, api_key: str | None = None):
        key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not key or key == "your-anthropic-api-key-here":
            raise RuntimeError("ANTHROPIC_API_KEY is not configured in .env")
        self.client = anthropic.Anthropic(api_key=key)

    # ---- perceive ---------------------------------------------------------
    def perceive(self, file_path: str) -> dict:
        """Returns {"mode": "image"|"text", "image_b64": ..., "media_type": ..., "text": ...}"""
        ext = Path(file_path).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            with open(file_path, "rb") as f:
                data = f.read()
            return {
                "mode": "image",
                "image_b64": base64.standard_b64encode(data).decode("utf-8"),
                "media_type": IMAGE_EXTENSIONS[ext],
            }
        if ext == ".pdf":
            with pdfplumber.open(file_path) as pdf:
                page = pdf.pages[0]
                text = (page.extract_text() or "").strip()
                if len(text) >= MIN_TEXT_LAYER_CHARS:
                    return {"mode": "text", "text": text}
                # scanned/photographed PDF: rasterize the page for a vision call
                pil_image = page.to_image(resolution=200).original
                buf = io.BytesIO()
                pil_image.save(buf, format="PNG")
                return {
                    "mode": "image",
                    "image_b64": base64.standard_b64encode(buf.getvalue()).decode("utf-8"),
                    "media_type": "image/png",
                }
        raise ValueError(f"Unsupported file type: {ext}")

    # ---- reason -------------------------------------------------------------
    def reason(self, perceived: dict) -> dict:
        if perceived["mode"] == "image":
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": perceived["media_type"],
                        "data": perceived["image_b64"],
                    },
                },
                {"type": "text", "text": "Extract the client fields from this document image."},
            ]
        else:
            content = [
                {
                    "type": "text",
                    "text": f"Extract the client fields from this document text:\n\n{perceived['text']}",
                }
            ]

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        text_blocks = [block.text for block in response.content if block.type == "text"]
        if not text_blocks:
            raise RuntimeError(f"No text block in Claude response: {response.content}")
        raw = text_blocks[0].strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)

    # ---- act (normalize) ------------------------------------------------
    def normalize(self, extracted: dict) -> dict:
        row = {
            "name": (extracted.get("name") or "").strip(),
            "entity": normalize_entity_type(extracted.get("entity", "")),
            "pan": (extracted.get("pan") or "").strip().upper(),
            "gstin": (extracted.get("gstin") or "").strip().upper(),
            "cin": (extracted.get("cin") or "").strip().upper(),
            "contact": (extracted.get("contact") or "").strip(),
            "mobile": (extracted.get("mobile") or "").strip(),
            "email": (extracted.get("email") or "").strip(),
            "address": (extracted.get("address") or "").strip(),
            "state": (extracted.get("state") or "").strip(),
            "sez": bool(extracted.get("sez", False)),
        }
        if not row["state"] and len(row["gstin"]) >= 2:
            row["state"] = GSTIN_STATE_CODES.get(row["gstin"][:2], "")
        if not row["pan"] and len(row["gstin"]) == 15:
            # GSTIN characters 3-12 are structurally the entity's PAN
            row["pan"] = row["gstin"][2:12]
        return row

    # ---- full loop --------------------------------------------------------
    def run(self, file_path: str) -> dict:
        perceived = self.perceive(file_path)
        extracted = self.reason(perceived)
        row = self.normalize(extracted)
        issues = validate_client_row(row)
        return {
            "source_file": os.path.basename(file_path),
            "row": row,
            "valid": not issues,
            "issues": issues,
        }


if __name__ == "__main__":
    import sys

    agent = OnboardingAgent()
    result = agent.run(sys.argv[1])
    print(json.dumps(result, indent=2))
