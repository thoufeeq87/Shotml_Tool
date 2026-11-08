"""Gemini (Google) provider."""

from google import genai
from google.genai import types

from .base import BaseProvider, ProviderError


class GeminiProvider(BaseProvider):
    name = "gemini"

    def generate(self, image_bytes, mime_type, prompt):
        client = genai.Client(
            api_key=self.api_key,
            # Newer Gemini models are served on v1beta only.
            http_options=types.HttpOptions(api_version="v1beta", timeout=self.timeout * 1000),
        )
        reply = client.models.generate_content(
            model=self.model,
            contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt],
            config=types.GenerateContentConfig(
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
            ),
        )
        if not (reply.text or "").strip():
            raise ProviderError("gemini: empty reply")
        return reply.text
