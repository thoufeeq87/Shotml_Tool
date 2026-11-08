"""Writes a finished slot's code to disk as a plain HTML file and a plain CSS file."""

from pathlib import Path

from django.utils.text import slugify


def slot_folder_name(slot):
    """A readable folder name such as 'screenshot-2-home-page'."""
    stem = slugify(Path(slot.original_name).stem) or "image"
    return f"screenshot-{slot.position}-{stem}"


def write_slot_files(slot, output_dir):
    """Save index.html and style.css in their own folder. Returns that folder.

    The HTML links to style.css, so each screenshot gets its own folder
    and the pair keeps working when opened in a browser.
    """
    folder = Path(output_dir) / slot_folder_name(slot)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "index.html").write_text(slot.html, encoding="utf-8")
    (folder / "style.css").write_text(slot.css, encoding="utf-8")
    return folder
