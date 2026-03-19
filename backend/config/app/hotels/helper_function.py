from .models import Hotel
from datetime import datetime

def _parse_date(value, field_name):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {field_name} format. Use YYYY-MM-DD")

def _load_hotel_and_dates(data):
    hotel_id = data.get("hotel_id")
    check_in = data.get("check_in")
    check_out = data.get("check_out")
    guests = int(data.get("guests", 1))

    if not hotel_id:
        raise ValueError("hotel_id is required")
    if not check_in or not check_out:
        raise ValueError("check_in and check_out are required")
    if guests < 1:
        raise ValueError("guests must be at least 1")

    hotel = Hotel.objects.filter(id=hotel_id).first()
    if not hotel:
        raise LookupError("Hotel not found")

    check_in_date = _parse_date(check_in, "check_in")
    check_out_date = _parse_date(check_out, "check_out")

    if check_out_date <= check_in_date:
        raise ValueError("check_out must be after check_in")

    if hotel.price_per_night is None:
        raise ValueError("Hotel pricing is not available")

    return hotel, check_in_date, check_out_date, guests

def _calculate_hotel_total(hotel, check_in_date, check_out_date):
    number_of_nights = (check_out_date - check_in_date).days
    total_price = hotel.price_per_night * number_of_nights
    return number_of_nights, total_price