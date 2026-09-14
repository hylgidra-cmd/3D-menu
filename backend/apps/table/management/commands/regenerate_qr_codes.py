from django.conf import settings
from django.core.management.base import BaseCommand

from apps.table.models import Table


class Command(BaseCommand):
    """Re-renders every table's QR code PNG against the current
    FRONTEND_BASE_URL, without touching any table's token. Run this once
    after pointing FRONTEND_BASE_URL at a new public domain (e.g. moving
    off a LAN IP or switching custom domains) - existing QR codes were
    baked with whatever FRONTEND_BASE_URL was set when each table was
    created."""

    help = "Regenerate all table QR code images using the current FRONTEND_BASE_URL (tokens are unchanged)"

    def handle(self, *args, **options):
        self.stdout.write(f"FRONTEND_BASE_URL = {settings.FRONTEND_BASE_URL}")
        count = 0
        for table in Table.objects.all():
            table.generate_qr_code()
            table.save(update_fields=["qr_code"])
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Regenerated {count} QR code(s)."))
