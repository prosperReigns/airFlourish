from decimal import Decimal
from .models import PricingRule
from .models import ExchangeRate

def apply_pricing(resource_type, base_price, user_country=None):

    final_price = Decimal(base_price)

    rules = PricingRule.objects.filter(
        resource_type=resource_type,
        active=True
    )

    for rule in rules:

        if rule.country and rule.country != user_country:
            continue

        if rule.rule_type == "percentage":

            fee = final_price * (rule.value / 100)

        else:

            fee = rule.value

        final_price += fee

    return final_price

def convert_currency(amount, base, target):

    if base == target:
        return amount

    rate = ExchangeRate.objects.get(
        base_currency=base,
        target_currency=target
    )

    return amount * rate.rate