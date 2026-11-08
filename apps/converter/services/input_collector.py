"""Turns command line paths (files or one folder) into a list of image files."""

from pathlib import Path

from django.conf import settings

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class InputError(ValueError):
    """The given paths cannot be used."""


def collect_image_paths(paths):
    """Return up to MAX_FILES_PER_BATCH image paths from files or a single folder."""
    given = [Path(path) for path in paths]
    for path in given:
        if not path.exists():
            raise InputError(f"Cannot find: {path}")

    if len(given) == 1 and given[0].is_dir():
        found = sorted(p for p in given[0].iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)
        if not found:
            raise InputError(f"No PNG, JPG or WebP pictures in folder: {given[0]}")
    else:
        folders = [path for path in given if path.is_dir()]
        if folders:
            raise InputError("Give either one folder or a list of picture files, not both.")
        found = given

    if len(found) > settings.MAX_FILES_PER_BATCH:
        raise InputError(
            f"Found {len(found)} pictures. The limit is {settings.MAX_FILES_PER_BATCH} at a time."
        )
    return found
