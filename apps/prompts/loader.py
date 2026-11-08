"""Loads the AI prompt from its markdown file on every call, so edits apply instantly."""

from django.conf import settings


def load_prompt():
    return settings.PROMPT_FILE.read_text(encoding="utf-8")
