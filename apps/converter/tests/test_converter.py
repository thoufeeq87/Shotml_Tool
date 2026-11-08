import io
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.ai_providers.base import ProviderError
from apps.ai_providers.fallback import generate_with_fallback
from apps.converter.models import Batch, Slot
from apps.converter.services import batch_service
from apps.converter.services.output_parser import ParseError, build_preview, parse_reply
from apps.converter.services.upload_validation import validate_upload

REPLY = "```html\n<!DOCTYPE html><html><head><link rel=\"stylesheet\" href=\"style.css\"></head><body><h1>Hi</h1></body></html>\n```\n```css\nbody { margin: 0; }\n```"


def make_image(name="shot.png", fmt="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue())


class FakeProvider:
    def __init__(self, name, reply=None):
        self.name, self.reply = name, reply

    def generate(self, image_bytes, mime_type, prompt):
        if self.reply is None:
            raise RuntimeError("boom")
        return self.reply


class ValidationTests(TestCase):
    def test_accepts_valid_images(self):
        self.assertEqual(validate_upload([make_image(), make_image("a.jpg", "JPEG")]), [])

    def test_rejects_six_files(self):
        self.assertTrue(validate_upload([make_image() for _ in range(6)]))

    def test_rejects_non_image(self):
        self.assertTrue(validate_upload([SimpleUploadedFile("fake.png", b"not an image")]))

    @override_settings(MAX_UPLOAD_MB=0)
    def test_rejects_too_big(self):
        self.assertIn("too big", validate_upload([make_image()])[0])

    def test_rejects_empty(self):
        self.assertTrue(validate_upload([]))


class ParserTests(TestCase):
    def test_parse_reply(self):
        html, css = parse_reply(REPLY)
        self.assertIn("<h1>", html)
        self.assertIn("margin", css)

    def test_missing_css_raises(self):
        with self.assertRaises(ParseError):
            parse_reply("```html\n<p>x</p>\n```")

    def test_preview_inlines_css(self):
        html, css = parse_reply(REPLY)
        preview = build_preview(html, css)
        self.assertIn("<style>", preview)
        self.assertNotIn("style.css", preview)


class FallbackTests(TestCase):
    def test_second_provider_used_when_first_fails(self):
        result, name = generate_with_fallback(
            b"x", "image/png", "p", parse=parse_reply,
            providers=[FakeProvider("claude"), FakeProvider("gemini", REPLY)],
        )
        self.assertEqual(name, "gemini")
        self.assertEqual(len(result), 2)

    def test_bad_reply_moves_to_next_provider(self):
        _, name = generate_with_fallback(
            b"x", "image/png", "p", parse=parse_reply,
            providers=[FakeProvider("claude", "no code here"), FakeProvider("openai", REPLY)],
        )
        self.assertEqual(name, "openai")

    def test_all_fail(self):
        with self.assertRaises(ProviderError):
            generate_with_fallback(b"x", "image/png", "p", providers=[FakeProvider("claude")])


class BatchFlowTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        override = override_settings(MEDIA_ROOT=Path(self.media.name))
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(self.media.cleanup)

    def fake_generate(self, image_bytes, mime, prompt, parse=None):
        return parse(REPLY), "claude"

    def test_keep_saves_images_and_code(self):
        batch = batch_service.create_batch("s1", [make_image(), make_image("b.png")], keep_images=True)
        batch_service.process_batch(batch.pk, generate=self.fake_generate)
        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.DONE)
        self.assertEqual(batch.slots.filter(status=Slot.Status.DONE).count(), 2)
        self.assertTrue(all(slot.image for slot in batch.slots.all()))

    def test_delete_removes_images_but_keeps_code(self):
        batch = batch_service.create_batch("s1", [make_image()], keep_images=False)
        batch_service.process_batch(batch.pk, generate=self.fake_generate)
        slot = batch.slots.get()
        self.assertFalse(slot.image)
        self.assertTrue(slot.html)
        self.assertEqual(list(Path(self.media.name).rglob("*.png")), [])

    def test_failed_slot_does_not_stop_others(self):
        calls = {"n": 0}

        def flaky(image_bytes, mime, prompt, parse=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ProviderError("down")
            return parse(REPLY), "openai"

        batch = batch_service.create_batch("s1", [make_image(), make_image("b.png")], keep_images=True)
        batch_service.process_batch(batch.pk, generate=flaky)
        statuses = [slot.status for slot in batch.slots.all()]
        self.assertEqual(statuses, [Slot.Status.FAILED, Slot.Status.DONE])


class ViewTests(TestCase):
    def test_tool_page_is_home(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_start_rejects_bad_upload(self):
        response = self.client.post(reverse("converter:start"), {"screenshots": SimpleUploadedFile("x.png", b"nope")})
        self.assertEqual(response.status_code, 400)
        self.assertIn("errors", response.json())

    def test_other_session_cannot_read_batch(self):
        batch = Batch.objects.create(session_key="someone-else")
        self.client.get("/")
        self.assertEqual(self.client.get(reverse("converter:status", args=[batch.pk])).status_code, 404)
