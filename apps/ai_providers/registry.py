"""Builds the ordered list of providers from settings. Add a provider here to extend."""

from django.conf import settings

from .base import ProviderError
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider

PROVIDER_CLASSES = {
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
}


def build_providers():
    """Return providers in fallback order; ones without a key are skipped."""
    providers = []
    for name in settings.AI_PROVIDER_ORDER:
        cls = PROVIDER_CLASSES.get(name)
        if cls is None:
            continue
        config = settings.AI_PROVIDERS[name]
        try:
            providers.append(
                cls(
                    api_key=config["api_key"],
                    model=config["model"],
                    temperature=settings.AI_TEMPERATURE,
                    max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
                    timeout=settings.AI_TIMEOUT_SECONDS,
                )
            )
        except ProviderError:
            continue
    return providers
