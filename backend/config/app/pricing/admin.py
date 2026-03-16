from django.contrib import admin
from .models import PricingRule, ExchangeRate

@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "resource_type",
        "rule_type",
        "value",
        "active"
    )

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):

    list_display = (
        "base_currency",
        "target_currency",
        "rate",
        "updated_at"
    )