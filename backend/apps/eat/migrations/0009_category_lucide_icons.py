from django.db import migrations, models


def replace_legacy_icons(apps, schema_editor):
    Category = apps.get_model("eat", "Category")
    Category.objects.exclude(icon__in=["utensils", "drink", "dessert", "salad"]).update(icon="utensils")


class Migration(migrations.Migration):
    dependencies = [
        ("eat", "0008_category_icon"),
    ]

    operations = [
        migrations.RunPython(replace_legacy_icons, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="category",
            name="icon",
            field=models.CharField(default="utensils", max_length=16),
        ),
    ]
