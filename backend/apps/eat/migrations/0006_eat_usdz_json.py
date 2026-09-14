from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eat', '0005_eat_model_file_usdz'),
    ]

    operations = [
        migrations.AddField(
            model_name='eat',
            name='usdz_json',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
