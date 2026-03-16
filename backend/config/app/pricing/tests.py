from decimal import Decimal

from django.test import TestCase

from app.pricing.models import PricingRule, ExchangeRate


class PricingRuleModelTests(TestCase):
    def test_active_defaults_true(self):
        rule = PricingRule.objects.create(
            name="Base Rule",
            resource_type="flight",
            rule_type="percentage",
            value=Decimal("5.00"),
        )
        self.assertTrue(rule.active)

    def test_country_optional(self):
        rule = PricingRule.objects.create(
            name="Global Rule",
            resource_type="hotel",
            rule_type="flat",
            value=Decimal("10.00"),
            country=None,
        )
        self.assertIsNone(rule.country)

    def test_rule_type_saved(self):
        rule = PricingRule.objects.create(
            name="Flat Rule",
            resource_type="visa",
            rule_type="flat",
            value=Decimal("20.00"),
        )
        self.assertEqual(rule.rule_type, "flat")


class ExchangeRateModelTests(TestCase):
    def test_updated_at_set(self):
        rate = ExchangeRate.objects.create(
            base_currency="USD",
            target_currency="NGN",
            rate=Decimal("1500.000000"),
        )
        self.assertIsNotNone(rate.updated_at)
