from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.eat.models import Eat, usdz_error_payload
from utils.glb_normalize import GLBNormalizeError, TARGET_MAX_DIMENSION, normalize_glb_bytes
from utils.usdz_convert import USDZConversionError, convert_glb_to_usdz, find_blender_binary


class Command(BaseCommand):
    help = (
        "Bakes TARGET_MAX_DIMENSION into every existing Eat's model_file "
        "that was saved before GLB normalization existed, then regenerates "
        "model_file_usdz from that normalized GLB - the safe way to backfill "
        "iOS support for models created before the USDZ pipeline existed, or "
        "to fix a USDZ that was baked at the old (pre-normalization) scale. "
        "No new 3D generation, no 3DAIStudio calls, ever. "
        "Never overwrites a file in place - normalized/converted output is "
        "always saved under a new name, so both the raw provider GLB and any "
        "previously-working USDZ remain in storage untouched unless the new "
        "one succeeds. Already-normalized GLBs (the marker embedded by "
        "normalize_glb_bytes) are left as-is, so this is safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing anything.")
        parser.add_argument("--eat-id", type=int, help="Only process this one Eat id.")
        parser.add_argument(
            "--skip-usdz", action="store_true",
            help="Only normalize GLBs; don't attempt USDZ conversion at all.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        eat_id = options.get("eat_id")
        skip_usdz = options["skip_usdz"]

        if not skip_usdz and not dry_run and not find_blender_binary():
            self.stdout.write(self.style.WARNING(
                "No Blender binary found (BLENDER_BINARY unset and `blender` not on PATH) - "
                "GLBs will still be normalized, but USDZ regeneration will be skipped for every item."
            ))

        queryset = Eat.objects.exclude(model_file="").order_by("id")
        if eat_id:
            queryset = queryset.filter(id=eat_id)

        stats = {
            "normalized": 0, "already_normalized": 0, "errors": 0,
            "usdz_regenerated": 0, "usdz_failed": 0,
        }

        for eat in queryset:
            try:
                with eat.model_file.open("rb") as f:
                    original_bytes = f.read()
            except (FileNotFoundError, OSError) as exc:
                self.stdout.write(self.style.WARNING(f"eat={eat.id}: model_file unreadable ({exc}), skipping"))
                stats["errors"] += 1
                continue

            try:
                normalized_bytes, info = normalize_glb_bytes(original_bytes)
            except GLBNormalizeError as exc:
                self.stdout.write(self.style.ERROR(f"eat={eat.id}: could not measure/normalize GLB ({exc}) - left untouched"))
                stats["errors"] += 1
                continue

            if info["changed"]:
                self.stdout.write(
                    f"eat={eat.id}: GLB {info['original_max_dimension']:.4f}m -> {TARGET_MAX_DIMENSION:.2f}m "
                    f"(scale={info['scale_applied']:.4f})"
                )
                stats["normalized"] += 1
                if not dry_run:
                    # New filename, never the original one - the raw
                    # provider download stays in storage as a backup.
                    eat.model_file.save(f"eat-{eat.id}-normalized.glb", ContentFile(normalized_bytes), save=True)
            else:
                self.stdout.write(f"eat={eat.id}: GLB already normalized")
                stats["already_normalized"] += 1

            if skip_usdz or dry_run:
                continue

            if self._regenerate_usdz(eat, normalized_bytes):
                stats["usdz_regenerated"] += 1
            else:
                stats["usdz_failed"] += 1

        suffix = " (dry run - nothing written)" if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"Done. normalized={stats['normalized']} already_normalized={stats['already_normalized']} "
            f"errors={stats['errors']} usdz_regenerated={stats['usdz_regenerated']} "
            f"usdz_failed={stats['usdz_failed']}{suffix}"
        ))

    def _regenerate_usdz(self, eat, normalized_glb_bytes) -> bool:
        """Never overwrites a working USDZ until the new conversion has
        already succeeded and validated - see convert_glb_to_usdz."""
        try:
            usdz_bytes = convert_glb_to_usdz(normalized_glb_bytes)
        except USDZConversionError as exc:
            self.stdout.write(self.style.WARNING(
                f"eat={eat.id}: USDZ regeneration failed ({exc.error_type}) - "
                f"existing USDZ (if any) left as-is"
            ))
            eat.usdz_json = usdz_error_payload(exc.error_type)
            eat.save(update_fields=["usdz_json"])
            return False
        except Exception:
            self.stdout.write(self.style.ERROR(f"eat={eat.id}: unexpected error during USDZ regeneration"))
            eat.usdz_json = usdz_error_payload("UNKNOWN_ERROR")
            eat.save(update_fields=["usdz_json"])
            return False

        eat.usdz_json = {}
        eat.model_file_usdz.save(f"eat-{eat.id}-normalized.usdz", ContentFile(usdz_bytes), save=True)
        self.stdout.write(self.style.SUCCESS(f"eat={eat.id}: USDZ regenerated"))
        return True
