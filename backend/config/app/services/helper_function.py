from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from django.conf import settings
from app.pricing.services import convert_currency
from app.pricing.models import ExchangeRate

def _get_country_code(user):
    country = getattr(user, "country", None)
    if hasattr(country, "code"):
        return country.code
    if country:
        return str(country)
    return None

def _get_user_currency(user, fallback_currency):
    country_code = _get_country_code(user)
    currency_map = getattr(settings, "COUNTRY_CURRENCY_MAP", {})
    return currency_map.get(country_code, fallback_currency)

def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None

def _quantize_amount(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _convert_amount(amount, base_currency, target_currency):
    if amount is None:
        return None
    if base_currency == target_currency:
        return amount
    try:
        return convert_currency(amount, base_currency, target_currency)
    except ExchangeRate.DoesNotExist:
        return None
