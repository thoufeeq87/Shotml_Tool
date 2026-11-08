import io
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from PIL import Image

from apps.ai_providers.base import ProviderError
from apps.converter.models import Batch, Slot
from apps.converter.services.input_collector import InputError, collect_image_paths
from apps.converter.services.output_parser import parse_reply
from apps.converter.services.output_writer import slot_folder_name

REPLY = "```html\n<!DOCTYPE html><html><head><link rel=\"stylesheet\" href=\"style.css\"></head><body><h1>Hi</h1></body></html>\n```\n```css\nbody { margin: 0; }\n```"
GENERATE = "apps.converter.services.batch_service.generate_with_fallback"


def write_image(folder, name):
    path = Path(folder) / name
    Image.new("RGB", (10, 10), "white").save(path)
    return path


class CollectorTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_folder_returns_only_images_sorted(self):
        write_image(self.temp.name, "b.png")
        write_image(self.temp.name, "a.jpg")
        (Path(self.temp.name) / "notes.txt").write_text("x")
        names = [p.name for p in collect_image_paths([self.temp.name])]
        self.assertEqual(names, ["a.jpg", "b.png"])

    def test_missing_path_rejected(self):
        with self.assertRaises(InputError):
            collect_image_paths([str(Path(self.temp.name) / "nope.png")])

    def test_more_than_five_rejected(self):
        paths = [write_image(self.temp.name, f"{i}.png") for i in range(6)]
        with self.assertRaises(InputError):
            collect_image_paths([str(p) for p in paths])

    def test_folder_mixed_with_files_rejected(self):
        image = write_image(self.temp.name, "a.png")
        with self.assertRaises(InputError):
            collect_image_paths([self.temp.name, str(image)])


class ConvertScreenshotsCommandTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        media = override_settings(MEDIA_ROOT=Path(self.temp.name) / "media")
        media.enable()
        self.addCleanup(media.disable)
        self.pictures = Path(self.temp.name) / "pictures"
        self.pictures.mkdir()
        self.output = Path(self.temp.name) / "out"

    def run_command(self, *args):
        out = StringIO()
        call_command("convert_screenshots", *args, "--output-dir", str(self.output), stdout=out, stderr=StringIO())
        return out.getvalue()

    def test_converts_and_writes_files(self):
        first = write_image(self.pictures, "home page.png")
        second = write_image(self.pictures, "pricing.png")
        with mock.patch(GENERATE, side_effect=lambda *a, parse=None, **k: (parse(REPLY), "gemini")):
            text = self.run_command(str(first), str(second))

        self.assertIn("2 of 2 done", text)
        self.assertIn("made by gemini", text)
        self.assertIn("Done:   2", text)
        folder = self.output / "screenshot-1-home-page"
        self.assertIn("<h1>", (folder / "index.html").read_text(encoding="utf-8"))
        self.assertIn("margin", (folder / "style.css").read_text(encoding="utf-8"))
        self.assertEqual(Batch.objects.get().session_key, "command-line")

    def test_failed_screenshot_is_reported_and_others_continue(self):
        first = write_image(self.pictures, "a.png")
        second = write_image(self.pictures, "b.png")
        calls = {"n": 0}

        def flaky(*args, parse=None, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise ProviderError("down")
            return parse(REPLY), "openai"

        with mock.patch(GENERATE, side_effect=flaky):
            with self.assertRaises(CommandError):
                self.run_command(str(first), str(second))

        self.assertEqual([s.status for s in Slot.objects.order_by("position")], ["failed", "done"])
        self.assertTrue((self.output / "screenshot-2-b" / "index.html").exists())
        self.assertFalse((self.output / "screenshot-1-a").exists())

    def test_delete_option_removes_stored_pictures(self):
        image = write_image(self.pictures, "a.png")
        with mock.patch(GENERATE, side_effect=lambda *a, parse=None, **k: (parse(REPLY), "claude")):
            self.run_command(str(image), "--images", "delete")
        self.assertEqual(list((Path(self.temp.name) / "media").rglob("*.png")), [])
        self.assertTrue(image.exists())  # the original file is never touched

    def test_invalid_file_stops_before_any_batch(self):
        bad = self.pictures / "fake.png"
        bad.write_bytes(b"not an image")
        with self.assertRaises(CommandError):
            self.run_command(str(bad))
        self.assertEqual(Batch.objects.count(), 0)

    def test_folder_name_is_readable(self):
        slot = Slot(position=3, original_name="My Hero Section.PNG")
        self.assertEqual(slot_folder_name(slot), "screenshot-3-my-hero-section")
