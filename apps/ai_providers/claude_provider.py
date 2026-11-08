"""Claude (Anthropic) provider."""

import base64

import anthropic

from .base import BaseProvider, ProviderError


class ClaudeProvider(BaseProvider):
    name = "claude"

    def generate(self, image_bytes, mime_type, prompt):
        client = anthropic.Anthropic(api_key=self.api_key, timeout=self.timeout)
        image = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": mime_type,
                "data": base64.b64encode(image_bytes).decode("ascii"),
            },
        }
        request = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": [image, {"type": "text", "text": prompt}]}],
        }
        # The SDK has no temperature argument, so it travels in the request body.
        try:
            reply = client.messages.create(**request, extra_body={"temperature": self.temperature})
        except anthropic.BadRequestError as error:
            if "temperature" not in str(error).lower():
                raise
            reply = client.messages.create(**request)  # this model does not accept temperature

        text = "".join(block.text for block in reply.content if block.type == "text")
        if not text.strip():
            raise ProviderError("claude: empty reply")
        return text
