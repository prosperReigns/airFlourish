from django.test import TestCase

from app.maintenance.apps import MaintenanceConfig


class MaintenanceConfigTests(TestCase):
    def test_app_name(self):
        self.assertEqual(MaintenanceConfig.name, "app.maintenance")

    def test_default_auto_field(self):
        self.assertEqual(MaintenanceConfig.default_auto_field, "django.db.models.BigAutoField")

    def test_label(self):
        self.assertEqual(MaintenanceConfig.label, "maintenance")

    def test_verbose_name(self):
        self.assertEqual(MaintenanceConfig.verbose_name, "Maintenance")
