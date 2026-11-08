"""Checks uploaded files before anything is saved."""

from django.conf import settings
from PIL import Image, UnidentifiedImageError

PIL_FORMAT_TO_MIME = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


def validate_upload(files):
    """Return a list of friendly error messages (empty list means all good)."""
    if not files:
        return ["Please choose at least one screenshot."]
    if len(files) > settings.MAX_FILES_PER_BATCH:
        return [f"You can upload up to {settings.MAX_FILES_PER_BATCH} screenshots at a time."]

    errors = []
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    for file in files:
        if file.size > max_bytes:
            errors.append(f"{file.name} is too big. The limit is {settings.MAX_UPLOAD_MB} MB.")
        elif detect_mime(file) is None:
            errors.append(f"{file.name} is not a PNG, JPG or WebP picture.")
    return errors


def detect_mime(file):
    """Read the real image type from the file contents, not the file name."""
    try:
        file.seek(0)
        with Image.open(file) as image:
            image.verify()
            return PIL_FORMAT_TO_MIME.get(image.format)
    except (UnidentifiedImageError, OSError, SyntaxError):
        return None
    finally:
        file.seek(0)
