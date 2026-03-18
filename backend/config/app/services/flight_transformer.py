from datetime import datetime
import re
import copy

def parse_iso_duration(duration_str):
    """
    Converts ISO 8601 duration (e.g., PT10H35M) to human-readable format like "10h 35m".
    """
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", duration_str)
    if not match:
        return duration_str
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    return f"{hours}h {minutes}m"

def simplify_flight_offer(raw_offer):
    """
    Convert a raw Amadeus flight offer into a simplified dictionary for frontend.
    """
    itineraries = raw_offer.get("itineraries", [])
    first_itinerary = itineraries[0] if itineraries else {}

    segments = first_itinerary.get("segments", [])
    departure_info = segments[0]["departure"] if segments else {}
    arrival_info = segments[-1]["arrival"] if segments else {}

    # keep a pristine copy for booking (no duration conversion)
    raw_offer_copy = copy.deepcopy(raw_offer)

    simplified = {
        "id": raw_offer.get("id"),
        "price": raw_offer.get("price", {}).get("total"),
        "currency": raw_offer.get("price", {}).get("currency"),
        "departure": departure_info.get("iataCode"),
        "arrival": arrival_info.get("iataCode"),
        "departure_time": departure_info.get("at"),
        "arrival_time": arrival_info.get("at"),
        "duration": parse_iso_duration(first_itinerary.get("duration", "")),
        "stops": max(len(segments) - 1, 0),
        "airline": raw_offer.get("validatingAirlineCodes", [None])[0],
        "raw_offer": raw_offer_copy,
    }
    return simplified

def simplify_flight_offers(raw_offers):
    """
    Simplify a list of raw flight offers.
    """
    if not isinstance(raw_offers, list):
        return []
    return [simplify_flight_offer(offer) for offer in raw_offers if isinstance(offer, dict)]
