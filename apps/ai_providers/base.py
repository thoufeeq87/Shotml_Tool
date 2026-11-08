"""Common interface every AI provider follows."""


class ProviderError(Exception):
    """Raised when a provider cannot return a usable answer."""


class BaseProvider:
    name = "base"

    def __init__(self, api_key, model, temperature, max_tokens, timeout):
        if not api_key:
            raise ProviderError(f"{self.name}: no API key set")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def generate(self, image_bytes, mime_type, prompt):
        """Return the model's text reply for one image and prompt."""
        raise NotImplementedError
