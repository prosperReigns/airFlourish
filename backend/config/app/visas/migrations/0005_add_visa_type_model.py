from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


def seed_visa_types(apps, schema_editor):
    VisaType = apps.get_model("visas", "VisaType")
    VisaApplication = apps.get_model("visas", "VisaApplication")

    for application in VisaApplication.objects.all():
        name = (application.visa_type or "").strip()
        if not name:
            continue
        code = slugify(name).replace("-", "_") or name.lower()
        visa_type, _ = VisaType.objects.get_or_create(
            code=code,
            defaults={"name": name},
        )
        application.visa_type_ref = visa_type
        application.save(update_fields=["visa_type_ref"])


class Migration(migrations.Migration):

    dependencies = [
        ("visas", "0004_add_booking_to_visaapplication"),
    ]

    operations = [
        migrations.CreateModel(
            name="VisaType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("country", models.CharField(blank=True, max_length=2)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddField(
            model_name="visaapplication",
            name="visa_type_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="applications",
                to="visas.visatype",
            ),
        ),
        migrations.RunPython(seed_visa_types, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="visaapplication",
            name="visa_type",
        ),
        migrations.RenameField(
            model_name="visaapplication",
            old_name="visa_type_ref",
            new_name="visa_type",
        ),
        migrations.AddIndex(
            model_name="visatype",
            index=models.Index(fields=["country", "is_active"], name="visas_visat_country_3b7f7d_idx"),
        ),
    ]
