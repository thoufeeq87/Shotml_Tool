"""OpenAI provider."""

import base64

import openai

from .base import BaseProvider, ProviderError


class OpenAIProvider(BaseProvider):
    name = "openai"

    def generate(self, image_bytes, mime_type, prompt):
        client = openai.OpenAI(api_key=self.api_key, timeout=self.timeout)
        data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        reply = client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_completion_tokens=self.max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        )
        text = reply.choices[0].message.content or ""
        if not text.strip():
            raise ProviderError("openai: empty reply")
        return text
