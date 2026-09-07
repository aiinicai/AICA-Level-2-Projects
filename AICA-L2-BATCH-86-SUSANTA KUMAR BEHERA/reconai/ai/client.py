import base64
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class AIClient:
    """
    Centralized multi-provider LLM wrapper.
    Supports both Google Gemini (Gemini 2.5 Flash / Gemini 1.5 Pro) and
    Anthropic Claude (Claude 3.5 Sonnet / Claude 3 Haiku).
    Supports text generation, JSON extraction, and multimodal vision OCR.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        provider: Optional[str] = None,
    ):
        self.model = model or "gemini-2.5-flash"
        
        # Determine provider: 'anthropic' or 'gemini'
        if provider:
            self.provider = provider.lower()
        elif "claude" in self.model.lower():
            self.provider = "anthropic"
        else:
            self.provider = "gemini"

        # Resolve API key based on provider or explicit argument
        if api_key and str(api_key).strip():
            self.api_key = str(api_key).strip()
            if self.api_key.startswith("sk-ant-"):
                self.provider = "anthropic"
        elif self.provider == "anthropic":
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        else:
            self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        self._client = None

    @property
    def is_available(self) -> bool:
        """Returns True if an API key is available for the configured provider."""
        return bool(self.api_key and str(self.api_key).strip())

    def _get_client(self):
        if self._client is None:
            if not self.is_available:
                raise ValueError(f"{self.provider.capitalize()} API key is not configured.")

            if self.provider == "anthropic":
                try:
                    import anthropic
                    self._client = anthropic.Client(api_key=self.api_key)
                except ImportError:
                    raise ImportError("anthropic SDK is not installed. Run 'pip install anthropic'.")
            else:
                try:
                    from google import genai
                    self._client = genai.Client(api_key=self.api_key)
                except ImportError:
                    raise ImportError("google-genai SDK is not installed. Run 'pip install google-genai'.")

        return self._client

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.1,
    ) -> str:
        """Generates text from either Claude or Gemini."""
        client = self._get_client()

        if self.provider == "anthropic":
            try:
                model_name = self.model if "claude" in self.model else "claude-3-5-sonnet-20241022"
                resp = client.messages.create(
                    model=model_name,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_instruction or "",
                    messages=[{"role": "user", "content": prompt}],
                )
                text_content = ""
                for block in resp.content:
                    if hasattr(block, "text"):
                        text_content += block.text
                return text_content
            except Exception as e:
                logger.error(f"Claude AI generate_text failed: {e}")
                raise
        else:
            try:
                config = {
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                }
                if system_instruction:
                    config["system_instruction"] = system_instruction

                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                return response.text or ""
            except Exception as e:
                logger.error(f"Gemini AI generate_text failed: {e}")
                raise

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        max_tokens: int = 4000,
    ) -> Union[List[Any], Dict[str, Any]]:
        """Generates content and parses output JSON array or object."""
        raw_text = self.generate_text(
            prompt=prompt,
            system_instruction=system_instruction,
            max_tokens=max_tokens,
            temperature=0.0,
        )
        return self._extract_json(raw_text)

    def generate_json_multimodal(
        self,
        prompt: str,
        mime_type: str,
        file_bytes: bytes,
        system_instruction: Optional[str] = None,
        max_tokens: int = 4000,
    ) -> Union[List[Any], Dict[str, Any]]:
        """Extracts structured JSON from images or documents using Gemini or Claude Vision."""
        client = self._get_client()

        if self.provider == "anthropic":
            try:
                model_name = self.model if "claude" in self.model else "claude-3-5-sonnet-20241022"
                b64_data = base64.b64encode(file_bytes).decode("utf-8")
                resp = client.messages.create(
                    model=model_name,
                    max_tokens=max_tokens,
                    system=system_instruction or "",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": mime_type if "image" in mime_type else "image/png",
                                        "data": b64_data,
                                    },
                                },
                                {"type": "text", "text": prompt},
                            ],
                        }
                    ],
                )
                text_content = "".join([b.text for b in resp.content if hasattr(b, "text")])
                return self._extract_json(text_content)
            except Exception as e:
                logger.error(f"Claude Vision call failed: {e}")
                raise
        else:
            try:
                from google.genai import types
                part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)

                config = {
                    "max_output_tokens": max_tokens,
                    "temperature": 0.0,
                }
                if system_instruction:
                    config["system_instruction"] = system_instruction

                response = client.models.generate_content(
                    model=self.model,
                    contents=[part, prompt],
                    config=config,
                )
                raw_text = response.text or ""
                return self._extract_json(raw_text)
            except Exception as e:
                logger.error(f"Gemini Multimodal OCR call failed: {e}")
                raise

    @staticmethod
    def _extract_json(text: str) -> Union[List[Any], Dict[str, Any]]:
        """Safely extracts JSON from markdown code fences or plain text."""
        cleaned = text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()
        else:
            match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON from AI response: {e}\nRaw output: {text[:500]}")
            raise
