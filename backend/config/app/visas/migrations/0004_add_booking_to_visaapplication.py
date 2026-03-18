from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("bookings", "0003_bookinglock"),
        ("visas", "0003_refactor_visa_workflow"),
    ]

    operations = [
        migrations.AddField(
            model_name="visaapplication",
            name="booking",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="visa_application",
                to="bookings.booking",
            ),
        ),
    ]
