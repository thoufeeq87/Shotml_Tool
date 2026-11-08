"""Small template helpers. They only reformat data; the real work stays in the services."""

from django import template

from ..services.output_parser import build_preview

register = template.Library()

PROVIDER_LABELS = {"claude": "Claude", "gemini": "Gemini", "openai": "OpenAI"}


@register.filter
def provider_label(provider):
    """'openai' becomes 'OpenAI'."""
    return PROVIDER_LABELS.get(provider, str(provider).capitalize())


@register.filter
def preview_document(slot):
    """The slot's HTML with its CSS inlined, ready for an iframe."""
    return build_preview(slot.html, slot.css)
