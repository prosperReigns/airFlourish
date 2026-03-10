from .models import Hotel

def extract_hotel_info(hotel_data):
    """
    Normalizes hotel data from:
    - Admin-created Hotel model instance
    - External Booking API response (dict or list)
    """

    # -----------------------------------------
    # CASE 1: ADMIN HOTEL (Django Model)
    # -----------------------------------------
    if isinstance(hotel_data, Hotel):
        return {
            "hotel_name": hotel_data.hotel_name,
            "address": hotel_data.address or "",
            "city": hotel_data.city,
            "country": str(hotel_data.country),
            "available_rooms": hotel_data.available_rooms,
            "booking_url": None,
            "rooms": hotel_data.rooms or [],
        }

    # -----------------------------------------
    # CASE 2: External API (list response)
    # -----------------------------------------
    if isinstance(hotel_data, list):
        if not hotel_data:
            return {}
        hotel = hotel_data[0]
    elif isinstance(hotel_data, dict):
        hotel = hotel_data
    else:
        return {}

    hotel_info = {
        "hotel_name": hotel.get("hotel_name"),
        "address": hotel.get("hotel_address_line"),
        "city": hotel.get("city"),
        "country": hotel.get("country_trans"),
        "available_rooms": hotel.get("available_rooms", 0),
        "booking_url": hotel.get("url"),
        "rooms": []
    }

    for block in hotel.get("block", []):
        room = {
            "room_name": block.get("name"),
            "price": block.get("min_price", {}).get("price"),
            "currency": block.get("min_price", {}).get("currency"),
            "refundable": block.get("paymentterms", {})
                            .get("cancellation", {})
                            .get("type") != "non_refundable",
            "highlights": [],
            "photos": []
        }

        room_id = str(block.get("room_id"))

        room_details = hotel.get("rooms", {}).get(room_id, {})

        room["highlights"] = [
            h.get("translated_name")
            for h in room_details.get("highlights", [])
        ]

        room["photos"] = [
            p.get("url_original")
            for p in room_details.get("photos", [])
        ]

        hotel_info["rooms"].append(room)

    return hotel_info