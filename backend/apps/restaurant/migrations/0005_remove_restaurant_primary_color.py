from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("restaurant", "0004_alter_restaurant_id_alter_restaurantstaff_id"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="restaurant",
            name="primary_color",
        ),
    ]
