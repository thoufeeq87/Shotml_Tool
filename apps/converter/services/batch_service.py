"""Creates batches and converts their screenshots one at a time in a background thread."""

import logging
import threading

from django.core.files.base import ContentFile
from django.db import close_old_connections

from apps.ai_providers.fallback import generate_with_fallback
from apps.prompts.loader import load_prompt

from ..models import Batch, Slot
from .cleanup import delete_batch_files, delete_slot_image
from .output_parser import parse_reply
from .upload_validation import detect_mime

logger = logging.getLogger(__name__)


def create_batch(session_key, files, keep_images):
    """Save the files and one Slot per file. Returns the new Batch."""
    batch = Batch.objects.create(session_key=session_key, keep_images=keep_images)
    for position, file in enumerate(files, start=1):
        slot = Slot(batch=batch, position=position, original_name=file.name[:255])
        slot.image.save(file.name, ContentFile(file.read()), save=False)
        slot.save()
    return batch


def start_batch(batch_id, only_pending=False):
    """Run the conversion in a background thread so the page stays responsive."""
    threading.Thread(
        target=process_batch, args=(batch_id,), kwargs={"only_pending": only_pending}, daemon=True
    ).start()


def retry_slot(slot):
    """Queue one failed screenshot to run again. Returns False if it cannot be retried."""
    if slot.status != Slot.Status.FAILED or not slot.image:
        return False
    slot.status = Slot.Status.PENDING
    slot.error = ""
    slot.save(update_fields=["status", "error"])
    Batch.objects.filter(pk=slot.batch_id).update(status=Batch.Status.RUNNING)
    start_batch(slot.batch_id, only_pending=True)
    return True


def process_batch(batch_id, generate=None, on_slot_start=None, on_slot_done=None, only_pending=False):
    """Convert each slot in order. A failed slot never stops the others.

    The optional callbacks receive the slot before and after it is converted;
    the command line uses them to print live progress. With only_pending,
    slots that are already finished are skipped (used by retry).
    """
    generate = generate or generate_with_fallback
    close_old_connections()
    try:
        batch = Batch.objects.get(pk=batch_id)
        prompt = load_prompt()
        slots = batch.slots.filter(status=Slot.Status.PENDING) if only_pending else batch.slots.all()
        for slot in slots:
            if on_slot_start:
                on_slot_start(slot)
            convert_slot(slot, prompt, generate)
            if not batch.keep_images:
                delete_slot_image(slot)
            if on_slot_done:
                on_slot_done(slot)
    except Exception:
        logger.exception("Batch %s crashed", batch_id)
    finally:
        Batch.objects.filter(pk=batch_id).update(status=Batch.Status.DONE)
        close_old_connections()


def convert_slot(slot, prompt, generate):
    slot.status = Slot.Status.WORKING
    slot.save(update_fields=["status"])
    try:
        with slot.image.open("rb") as handle:
            image_bytes = handle.read()
        mime = detect_mime(ContentFile(image_bytes))
        (html, css), provider = generate(image_bytes, mime, prompt, parse=parse_reply)
        slot.html, slot.css, slot.provider = html, css, provider
        slot.status = Slot.Status.DONE
    except Exception as error:
        logger.warning("Slot %s failed: %s", slot.pk, error)
        slot.status = Slot.Status.FAILED
        slot.error = "We could not convert this screenshot. Please try it again."
    slot.save()


def delete_batch(batch):
    """Remove a batch, its pictures and its code."""
    delete_batch_files(batch)
    batch.delete()
