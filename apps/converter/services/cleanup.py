"""Removes uploaded picture files."""

import shutil

from django.conf import settings


def delete_slot_image(slot):
    """Delete one slot's picture file and forget it."""
    if slot.image:
        slot.image.delete(save=False)
        slot.image = ""
        slot.save(update_fields=["image"])


def delete_batch_files(batch):
    """Delete every picture of a batch, including its folder."""
    for slot in batch.slots.all():
        delete_slot_image(slot)
    shutil.rmtree(settings.MEDIA_ROOT / "uploads" / str(batch.id), ignore_errors=True)
