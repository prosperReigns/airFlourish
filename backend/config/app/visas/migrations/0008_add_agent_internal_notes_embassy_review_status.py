from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("visas", "0007_merge_20260319_0808"),
    ]

    operations = [
        migrations.AddField(
            model_name="visaapplication",
            name="agent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="agent_visa_applications",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="visaapplication",
            name="embassy_review_status",
            field=models.CharField(blank=True, default="pending", max_length=50),
        ),
        migrations.AddField(
            model_name="visaapplication",
            name="internal_notes",
            field=models.TextField(blank=True),
        ),
    ]
