"""Thin views: they only read the request, call a service and return a response."""

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import Batch
from .services import batch_service
from .services.output_parser import build_preview
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


@require_GET
def tool(request):
    """The one and only page."""
    session_key = _session_key(request)
    past_batches = Batch.objects.filter(session_key=session_key, keep_images=True, status=Batch.Status.DONE)[:10]
    open_batch = request.GET.get("batch", "")
    return render(
        request,
        "converter/tool.html",
        {
            "past_batches": past_batches,
            "open_batch": open_batch,
            "max_files": settings.MAX_FILES_PER_BATCH,
            "max_mb": settings.MAX_UPLOAD_MB,
        },
    )


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
    return JsonResponse({"batch_id": str(batch.pk)})


@require_GET
def status(request, batch_id):
    """Progress plus the code of finished screenshots. `rendered` lists positions the page already has."""
    batch = _own_batch(request, batch_id)
    rendered = {int(p) for p in request.GET.get("rendered", "").split(",") if p.isdigit()}

    slots = []
    for slot in batch.slots.all():
        item = {
            "position": slot.position,
            "name": slot.original_name,
            "status": slot.status,
            "provider": slot.provider,
            "error": slot.error,
        }
        if slot.status == "done" and slot.position not in rendered:
            item.update(html=slot.html, css=slot.css, preview=build_preview(slot.html, slot.css))
        slots.append(item)

    return JsonResponse(
        {
            "status": batch.status,
            "total": len(slots),
            "done": batch.done_count,
            "keep_images": batch.keep_images,
            "slots": slots,
        }
    )


@require_POST
def delete(request, batch_id):
    """Remove a kept batch."""
    batch_service.delete_batch(_own_batch(request, batch_id))
    return JsonResponse({"deleted": True})
