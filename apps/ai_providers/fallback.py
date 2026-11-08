"""Tries providers one after another until one succeeds."""

import logging

from .base import ProviderError
from .registry import build_providers

logger = logging.getLogger(__name__)


def generate_with_fallback(image_bytes, mime_type, prompt, parse=None, providers=None):
    """Return (result, provider_name).

    `parse` turns the raw reply into the final result; a reply that fails to parse
    counts as a failure and the next provider is tried.
    Raises ProviderError if every provider fails.
    """
    providers = build_providers() if providers is None else providers
    if not providers:
        raise ProviderError("No AI provider is configured. Add an API key to .env.")

    for provider in providers:
        try:
            reply = provider.generate(image_bytes, mime_type, prompt)
            return (parse(reply) if parse else reply), provider.name
        except Exception as error:  # any SDK, network or parsing failure means: try the next one
            logger.warning("Provider %s failed: %s", provider.name, error)

    raise ProviderError("All AI services failed. Please try again in a moment.")
