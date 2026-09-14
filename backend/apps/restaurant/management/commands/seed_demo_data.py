import os
import random
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image

from apps.eat.models import Category, Eat
from apps.restaurant.models import Restaurant, RestaurantStaff
from apps.table.models import Table

User = get_user_model()

MENU_ITEMS = {
    "Taomlar": [
        ("Osh", "An'anaviy o'zbek oshi, guruch va go'sht bilan tayyorlanadi.", "35000"),
        ("Lag'mon", "Qo'lda tortilgan xamir, sabzavot va go'sht sousi bilan.", "30000"),
        ("Manti", "Bug'da pishirilgan, go'shtli manti, smetana bilan beriladi.", "28000"),
        ("Shashlik", "Cho'chqa go'shtidan tayyorlangan mazali shashlik.", "40000"),
    ],
    "Ichimliklar": [
        ("Choy", "Issiq qora yoki ko'k choy, tanlov bo'yicha.", "5000"),
        ("Kompot", "Mavsumiy mevalardan tayyorlangan uy kompoti.", "8000"),
        ("Limonad", "Uy sharoitida tayyorlangan sovuq limonad.", "10000"),
    ],
    "Desertlar": [
        ("Napoleon", "Qatlamli xamir tort, krem bilan.", "15000"),
        ("Muzqaymoq", "Vanil ta'mli muzqaymoq, ustidan siropli.", "12000"),
    ],
}

PALETTE = [
    (230, 126, 34), (46, 204, 113), (52, 152, 219),
    (155, 89, 182), (241, 196, 15), (231, 76, 60),
]


def _placeholder_image(label: str, size=(600, 400)) -> ContentFile:
    """A solid-color JPEG generated in-memory - no external image service or
    network access needed, works the same on any host."""
    color = random.choice(PALETTE)
    img = Image.new("RGB", size, color)
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=80)
    safe_label = "".join(c if c.isalnum() else "-" for c in label.lower())
    return ContentFile(buffer.getvalue(), name=f"{safe_label}.jpg")


class Command(BaseCommand):
    """Seeds one demo restaurant with categories, menu items, and tables so a
    fresh deploy isn't an empty shell. Only runs when SEED_DEMO_DATA is set
    (entrypoint.sh gates it), and skips outright if any restaurant already
    exists - safe to leave the env var set across redeploys."""

    help = "Create a demo restaurant with sample categories, eat items, and tables (idempotent)."

    def handle(self, *args, **options):
        if not os.environ.get("SEED_DEMO_DATA"):
            self.stdout.write("SEED_DEMO_DATA not set - skipping.")
            return

        if Restaurant.objects.exists():
            self.stdout.write("A restaurant already exists - skipping demo seed.")
            return

        with transaction.atomic():
            owner, created = User.objects.get_or_create(
                username="demo_owner",
                defaults={"email": "demo_owner@example.com"},
            )
            if created:
                owner.set_password("demo12345")
                owner.save()

            restaurant = Restaurant.objects.create(
                user=owner,
                name="Demo Restoran",
                description="Bu - tizimni sinash uchun avtomatik yaratilgan namunaviy restoran.",
                location="Toshkent, Amir Temur ko'chasi 1",
                cover_image=_placeholder_image("demo-cover", size=(1200, 400)),
            )
            RestaurantStaff.objects.create(restaurant=restaurant, user=owner, role=RestaurantStaff.Role.OWNER)

            for order, (category_name, items) in enumerate(MENU_ITEMS.items()):
                category = Category.objects.create(restaurant=restaurant, name=category_name, order=order)
                for name, description, price in items:
                    Eat.objects.create(
                        restaurant=restaurant,
                        category=category,
                        name=name,
                        description=description,
                        price=price,
                        image=_placeholder_image(name),
                    )

            tables = [Table.objects.create(restaurant=restaurant, name=f"Stol {i}", place="Zal") for i in range(1, 4)]

        self.stdout.write(self.style.SUCCESS(
            f"Demo data created: '{restaurant.name}' (login: demo_owner / demo12345). "
            f"Sample QR menu: {tables[0].menu_url()}"
        ))
