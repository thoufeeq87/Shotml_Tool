"""Root URLs: the tool page is the whole site (no landing page)."""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("", include("apps.converter.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
