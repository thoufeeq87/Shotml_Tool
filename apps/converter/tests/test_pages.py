import tempfile
from pathlib import Path
from unittest import mock

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.converter.models import Batch, Slot

HTML = '<!DOCTYPE html><html><head><link rel="stylesheet" href="style.css"></head><body><h1>Hi "there"</h1></body></html>'
CSS = "body { margin: 0; }"


class PageTestCase(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        override = override_settings(MEDIA_ROOT=Path(media.name))
        override.enable()
        self.addCleanup(override.disable)
        self.client.get(reverse("converter:converter"))  # creates the browser session
        self.session_key = self.client.session.session_key

    def make_batch(self, statuses, batch_status=Batch.Status.DONE, keep=True, with_image=True):
        batch = Batch.objects.create(session_key=self.session_key, keep_images=keep, status=batch_status)
        for position, status in enumerate(statuses, start=1):
            slot = Slot(batch=batch, position=position, original_name=f"shot{position}.png", status=status)
            if status == Slot.Status.DONE:
                slot.html, slot.css, slot.provider = HTML, CSS, "openai"
            if with_image:
                slot.image.save("x.png", ContentFile(b"data"), save=False)
            slot.save()
        return batch


class StaticPageTests(PageTestCase):
    def test_landing_page_has_start_button_and_one_h1(self):
        response = self.client.get(reverse("converter:landing"))
        self.assertContains(response, reverse("converter:converter"))
        self.assertContains(response, "Claude")
        self.assertEqual(response.content.decode().count("<h1"), 1)

    def test_converter_page_has_upload_box_and_choice(self):
        response = self.client.get(reverse("converter:converter"))
        self.assertContains(response, 'id="dropzone"')
        self.assertContains(response, 'value="keep"')
        self.assertContains(response, 'value="delete"')

    def test_base_template_defines_the_design_tokens_once(self):
        html = self.client.get(reverse("converter:landing")).content.decode()
        self.assertEqual(html.count("#fde047"), 1)
        self.assertEqual(html.count('"Space Mono"'), 1)  # heading font defined once in the Tailwind setup
        self.assertEqual(html.count("#fb923c"), 1)


class FlowPageTests(PageTestCase):
    def test_progress_page_shows_each_status(self):
        batch = self.make_batch(["done", "working", "pending", "failed"], batch_status=Batch.Status.RUNNING)
        html = self.client.get(reverse("converter:progress", args=[batch.pk])).content.decode()
        for label in ("Done", "Working", "Waiting", "Failed"):
            self.assertIn(f">{label}<", html)
        self.assertIn("2 of 4 done", html)

    def test_progress_redirects_to_results_when_finished(self):
        batch = self.make_batch(["done"])
        response = self.client.get(reverse("converter:progress", args=[batch.pk]))
        self.assertRedirects(response, reverse("converter:results", args=[batch.pk]))

    def test_results_redirects_to_progress_while_running(self):
        batch = self.make_batch(["working"], batch_status=Batch.Status.RUNNING)
        response = self.client.get(reverse("converter:results", args=[batch.pk]))
        self.assertRedirects(response, reverse("converter:progress", args=[batch.pk]))

    def test_status_json(self):
        batch = self.make_batch(["done", "pending"], batch_status=Batch.Status.RUNNING)
        data = self.client.get(reverse("converter:status", args=[batch.pk])).json()
        self.assertEqual((data["done"], data["total"]), (1, 2))
        self.assertEqual([s["status"] for s in data["slots"]], ["done", "pending"])

    def test_results_show_preview_code_and_ai_tag(self):
        batch = self.make_batch(["done"])
        response = self.client.get(reverse("converter:results", args=[batch.pk]))
        self.assertContains(response, "Made by OpenAI")
        self.assertContains(response, "<iframe")
        self.assertContains(response, "&lt;style&gt;")  # css inlined into the (escaped) preview
        self.assertContains(response, "&lt;h1&gt;Hi")  # code is escaped in its box
        self.assertContains(response, 'data-copy="slot-1-html-code"')
        self.assertContains(response, 'data-copy="slot-1-css-code"')

    def test_failed_slot_shows_retry_button(self):
        batch = self.make_batch(["failed"])
        response = self.client.get(reverse("converter:results", args=[batch.pk]))
        self.assertContains(response, "Retry this screenshot")

    def test_failed_slot_without_picture_has_no_retry_button(self):
        batch = self.make_batch(["failed"], keep=False, with_image=False)
        response = self.client.get(reverse("converter:results", args=[batch.pk]))
        self.assertNotContains(response, "Retry this screenshot")
        self.assertContains(response, "cannot be retried")

    def test_retry_requeues_the_slot_and_goes_to_progress(self):
        batch = self.make_batch(["done", "failed"])
        with mock.patch("apps.converter.services.batch_service.start_batch") as start:
            response = self.client.post(reverse("converter:retry", args=[batch.pk, 2]))
        self.assertRedirects(response, reverse("converter:progress", args=[batch.pk]), fetch_redirect_response=False)
        start.assert_called_once_with(batch.pk, only_pending=True)
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.RUNNING)
        self.assertEqual(batch.slots.get(position=2).status, Slot.Status.PENDING)
        self.assertEqual(batch.slots.get(position=1).status, Slot.Status.DONE)

    def test_retry_of_done_slot_does_nothing(self):
        batch = self.make_batch(["done"])
        with mock.patch("apps.converter.services.batch_service.start_batch") as start:
            self.client.post(reverse("converter:retry", args=[batch.pk, 1]))
        start.assert_not_called()

    def test_delete_batch_redirects_to_converter(self):
        batch = self.make_batch(["done"])
        response = self.client.post(reverse("converter:delete", args=[batch.pk]))
        self.assertRedirects(response, reverse("converter:converter"))
        self.assertFalse(Batch.objects.filter(pk=batch.pk).exists())

    def test_other_session_cannot_open_results(self):
        batch = Batch.objects.create(session_key="someone-else", status=Batch.Status.DONE)
        self.assertEqual(self.client.get(reverse("converter:results", args=[batch.pk])).status_code, 404)
