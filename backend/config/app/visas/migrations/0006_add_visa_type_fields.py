from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("visas", "0005_add_visa_type_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="visatype",
            name="price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="visatype",
            name="required_documents",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="visatype",
            name="processing_days",
            field=models.PositiveIntegerField(default=7),
        ),
    ]
