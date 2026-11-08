"""Run the whole screenshot-to-code process from the terminal.

Examples:
    python manage.py convert_screenshots home.png pricing.png
    python manage.py convert_screenshots ./mockups --images delete --output-dir ./code
"""

from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from apps.converter.models import Slot
from apps.converter.services import batch_service
from apps.converter.services.input_collector import InputError, collect_image_paths
from apps.converter.services.output_writer import write_slot_files
from apps.converter.services.upload_validation import validate_upload

CLI_SESSION_KEY = "command-line"


class Command(BaseCommand):
    help = "Convert up to 5 screenshots (or one folder of them) into plain HTML and CSS."

    def add_arguments(self, parser):
        parser.add_argument("paths", nargs="+", help="Up to 5 image files, or one folder of images.")
        parser.add_argument(
            "--images",
            choices=["keep", "delete"],
            default="keep",
            help="What happens to the stored pictures afterwards (default: keep).",
        )
        parser.add_argument(
            "--output-dir",
            default=str(settings.BASE_DIR / "output"),
            help="Folder where the HTML and CSS files are saved (default: ./output).",
        )

    def handle(self, *args, **options):
        files = self.open_files(options["paths"])
        try:
            errors = validate_upload(files)
            if errors:
                raise CommandError("\n".join(errors))

            batch = batch_service.create_batch(CLI_SESSION_KEY, files, options["images"] == "keep")
        finally:
            for file in files:
                file.close()

        output_dir = Path(options["output_dir"])
        self.stdout.write(f"Batch {batch.pk}: converting {len(files)} screenshot(s)...")

        batch_service.process_batch(
            batch.pk,
            on_slot_start=lambda slot: self.report_start(slot, len(files)),
            on_slot_done=lambda slot: self.report_done(slot, batch, len(files), output_dir),
        )
        self.print_summary(batch, output_dir, options["images"])

    # --- Input ---
    def open_files(self, paths):
        try:
            image_paths = collect_image_paths(paths)
        except InputError as error:
            raise CommandError(str(error))
        return [File(open(path, "rb"), name=path.name) for path in image_paths]

    # --- Live progress ---
    def report_start(self, slot, total):
        self.stdout.write(f"  Converting {slot.position} of {total}: {slot.original_name} ...")
        self.stdout.flush()

    def report_done(self, slot, batch, total, output_dir):
        done = batch.done_count
        if slot.status == Slot.Status.DONE:
            folder = write_slot_files(slot, output_dir)
            self.stdout.write(self.style.SUCCESS(f"  {done} of {total} done: {slot.original_name} made by {slot.provider} -> {folder}"))
        else:
            self.stdout.write(self.style.ERROR(f"  {done} of {total} done: {slot.original_name} FAILED on all AI services, skipping it."))
        self.stdout.flush()

    # --- Summary ---
    def print_summary(self, batch, output_dir, images):
        slots = list(batch.slots.all())
        done = [slot for slot in slots if slot.status == Slot.Status.DONE]
        failed = [slot for slot in slots if slot.status == Slot.Status.FAILED]
        providers = Counter(slot.provider for slot in done)

        self.stdout.write("\nSummary")
        self.stdout.write(f"  Done:   {len(done)}")
        self.stdout.write(f"  Failed: {len(failed)}")
        for name, count in providers.items():
            self.stdout.write(f"  Made by {name}: {count}")
        for slot in failed:
            self.stdout.write(f"  Failed file: {slot.original_name}")
        if done:
            self.stdout.write(f"  Code saved in: {output_dir}")
        self.stdout.write(f"  Pictures {'kept' if images == 'keep' else 'deleted'}.")

        if failed:
            raise CommandError(f"{len(failed)} screenshot(s) failed. Details are in the log above.")
