from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [("eat", "0008_category_icon"), ("restaurant", "0005_remove_restaurant_primary_color"), ("table", "0002_alter_table_id")]
    operations = [
        migrations.CreateModel(name="Order", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("status", models.CharField(choices=[("new", "Yangi"), ("accepted", "Qabul qilindi"), ("preparing", "Tayyorlanmoqda"), ("ready", "Tayyor"), ("served", "Yetkazildi"), ("cancelled", "Bekor qilindi")], default="new", max_length=16)),
            ("payment_method", models.CharField(choices=[("cash", "Naqd"), ("card", "Karta"), ("online", "Onlayn")], max_length=16)),
            ("note", models.CharField(blank=True, max_length=500)),
            ("total", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("restaurant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="restaurant.restaurant")),
            ("table", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to="table.table")),
        ], options={"ordering": ["-created_at"]}),
        migrations.CreateModel(name="OrderItem", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=200)), ("price", models.DecimalField(decimal_places=2, max_digits=10)), ("quantity", models.PositiveIntegerField()),
            ("eat", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="order_items", to="eat.eat")),
            ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="orders.order")),
        ], options={"ordering": ["id"]}),
    ]
