# DD-KARYO-007 D1 — silueta de cada cromosoma en píxeles de la metafase.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('samples', '0016_recrop_event'),
    ]

    operations = [
        migrations.AddField(
            model_name='chromosome',
            name='contour',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
