import uuid
from pathlib import Path

from django.db import models


def upload_path(instance, filename):
    """Store uploads under a random name so the original name never touches disk."""
    extension = Path(filename).suffix.lower()
    return f"uploads/{instance.batch_id}/{uuid.uuid4().hex}{extension}"


class Batch(models.Model):
    """One upload of up to five screenshots."""

    class Status(models.TextChoices):
        RUNNING = "running"
        DONE = "done"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=64, db_index=True)
    keep_images = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.RUNNING)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    @property
    def done_count(self):
        return self.slots.exclude(status__in=[Slot.Status.PENDING, Slot.Status.WORKING]).count()


class Slot(models.Model):
    """One screenshot inside a batch and its generated code."""

    class Status(models.TextChoices):
        PENDING = "pending"
        WORKING = "working"
        DONE = "done"
        FAILED = "failed"

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name="slots")
    position = models.PositiveSmallIntegerField()
    original_name = models.CharField(max_length=255)
    image = models.FileField(upload_to=upload_path, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    html = models.TextField(blank=True)
    css = models.TextField(blank=True)
    provider = models.CharField(max_length=20, blank=True)
    error = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["position"]
        unique_together = [("batch", "position")]
