"""Turns the model's reply into separate HTML and CSS, and builds the live preview page."""

import re

STYLESHEET_LINK = re.compile(r"<link[^>]*href=[\"']style\.css[\"'][^>]*>", re.IGNORECASE)
HEAD_CLOSE = re.compile(r"</head>", re.IGNORECASE)


class ParseError(ValueError):
    """The reply did not contain both an HTML and a CSS block."""


def _find_block(text, lang):
    pattern = r"```" + lang + r"[^\n]*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def parse_reply(text):
    """Return (html, css). Raises ParseError when either part is missing."""
    html = _find_block(text, "html")
    css = _find_block(text, "css")
    if not html or not css:
        raise ParseError("The AI reply did not contain both an HTML and a CSS block.")
    return html, css


def build_preview(html, css):
    """Merge CSS into the HTML so it can run inside a single iframe."""
    style_tag = f"<style>\n{css}\n</style>"
    if STYLESHEET_LINK.search(html):
        return STYLESHEET_LINK.sub(lambda _: style_tag, html, count=1)
    if HEAD_CLOSE.search(html):
        return HEAD_CLOSE.sub(lambda _: style_tag + "\n</head>", html, count=1)
    return style_tag + "\n" + html
