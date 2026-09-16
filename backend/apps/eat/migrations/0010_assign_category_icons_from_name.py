from django.db import migrations


def assign_icons_from_category_names(apps, schema_editor):
    Category = apps.get_model("eat", "Category")
    for category in Category.objects.filter(icon="utensils"):
        name = category.name.lower()
        if "ichimlik" in name:
            category.icon = "drink"
        elif "desert" in name or "shirin" in name:
            category.icon = "dessert"
        elif "salat" in name:
            category.icon = "salad"
        else:
            continue
        category.save(update_fields=["icon"])


class Migration(migrations.Migration):
    dependencies = [
        ("eat", "0009_category_lucide_icons"),
    ]

    operations = [
        migrations.RunPython(assign_icons_from_category_names, migrations.RunPython.noop),
    ]
