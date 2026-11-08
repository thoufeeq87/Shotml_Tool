"""Thin views: they only read the request, call a service and return a response."""

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .models import Batch, Slot
from .services import batch_service
from .services.upload_validation import validate_upload


def _session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _own_batch(request, batch_id):
    """Fetch a batch only if it belongs to this browser session."""
    batch = get_object_or_404(Batch, pk=batch_id)
    if batch.session_key != request.session.session_key:
        raise Http404
    return batch


def _limits():
    return {"max_files": settings.MAX_FILES_PER_BATCH, "max_mb": settings.MAX_UPLOAD_MB}


@require_GET
def landing(request):
    return render(request, "converter/landing.html", _limits())


@require_GET
def converter(request):
    session_key = _session_key(request)
    past_batches = Batch.objects.filter(session_key=session_key, keep_images=True, status=Batch.Status.DONE)[:10]
    return render(request, "converter/converter.html", {"past_batches": past_batches, **_limits()})


@require_POST
def start(request):
    """Validate the upload, save it and begin converting."""
    files = request.FILES.getlist("screenshots")
    errors = validate_upload(files)
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    keep_images = request.POST.get("keep_images", "keep") == "keep"
    batch = batch_service.create_batch(_session_key(request), files, keep_images)
    batch_service.start_batch(batch.pk)
    return JsonResponse({"batch_id": str(batch.pk), "progress_url": reverse("converter:progress", args=[batch.pk])})


@require_GET
def progress(request, batch_id):
    batch = _own_batch(request, batch_id)
    if batch.status == Batch.Status.DONE:
        return redirect("converter:results", batch_id=batch.pk)
    return render(request, "converter/progress.html", {"batch": batch, "slots": batch.slots.all()})


@require_GET
def status(request, batch_id):
    """Progress numbers and each screenshot's status, for the progress page to poll."""
    batch = _own_batch(request, batch_id)
    slots = [{"position": s.position, "status": s.status} for s in batch.slots.all()]
    return JsonResponse({"status": batch.status, "total": len(slots), "done": batch.done_count, "slots": slots})


@require_GET
def results(request, batch_id):
    batch = _own_batch(request, batch_id)
    if batch.status != Batch.Status.DONE:
        return redirect("converter:progress", batch_id=batch.pk)
    slots = list(batch.slots.all())
    finished = sum(1 for slot in slots if slot.status == Slot.Status.DONE)
    return render(request, "converter/results.html", {"batch": batch, "slots": slots, "finished": finished})


@require_POST
def retry(request, batch_id, position):
    """Run one failed screenshot again."""
    batch = _own_batch(request, batch_id)
    slot = get_object_or_404(batch.slots, position=position)
    if batch_service.retry_slot(slot):
        return redirect("converter:progress", batch_id=batch.pk)
    return redirect("converter:results", batch_id=batch.pk)


@require_POST
def delete(request, batch_id):
    """Remove a kept batch."""
    batch_service.delete_batch(_own_batch(request, batch_id))
    return redirect("converter:converter")
