from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase

from app.inventory.models import Inventory


class InventoryModelTests(TestCase):
    def test_metadata_optional(self):
        inventory = Inventory.objects.create(
            provider="amadeus",
            resource_type="flight",
            resource_id="fl-001",
            available_quantity=10,
            price=Decimal("200.00"),
            currency="USD",
        )
        self.assertIsNone(inventory.metadata)

    def test_unique_together_enforced(self):
        Inventory.objects.create(
            provider="amadeus",
            resource_type="flight",
            resource_id="fl-unique",
            available_quantity=5,
            price=Decimal("150.00"),
            currency="USD",
        )
        with self.assertRaises(IntegrityError):
            Inventory.objects.create(
                provider="amadeus",
                resource_type="flight",
                resource_id="fl-unique",
                available_quantity=7,
                price=Decimal("180.00"),
                currency="USD",
            )

    def test_last_synced_set(self):
        inventory = Inventory.objects.create(
            provider="amadeus",
            resource_type="flight",
            resource_id="fl-sync",
            available_quantity=2,
            price=Decimal("90.00"),
            currency="USD",
        )
        self.assertIsNotNone(inventory.last_synced)

    def test_resource_type_saved(self):
        inventory = Inventory.objects.create(
            provider="amadeus",
            resource_type="hotel",
            resource_id="hotel-001",
            available_quantity=4,
            price=Decimal("120.00"),
            currency="USD",
        )
        self.assertEqual(inventory.resource_type, "hotel")
