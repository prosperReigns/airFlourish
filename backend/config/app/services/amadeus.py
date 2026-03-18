import logging

from amadeus import Client, ResponseError
from django.conf import settings

_amadeus_client = None
logger = logging.getLogger(__name__)


def _get_client():
    global _amadeus_client

    if _amadeus_client is None:
        missing = []
        if not settings.AMADEUS_API_KEY:
            missing.append("AMADEUS_API_KEY")
        if not settings.AMADEUS_API_SECRET:
            missing.append("AMADEUS_API_SECRET")
        if missing:
            raise RuntimeError(f"Amadeus credentials not configured: {', '.join(missing)}")
        _amadeus_client = Client(
            client_id=settings.AMADEUS_API_KEY,
            client_secret=settings.AMADEUS_API_SECRET,
        )

    return _amadeus_client

class AmadeusService:
    @staticmethod
    def search_flights(origin, destination, departure_date, return_date=None):
        try:
            client = _get_client()
            params = {
                "originLocationCode": origin,
                "destinationLocationCode": destination,
                "departureDate": departure_date,
                "adults": 1
            }

            if return_date:
                params["returnDate"] = return_date  # ✅ only add if it exists

            response = client.shopping.flight_offers_search.get(**params)
            return response.data
        except RuntimeError as e:
            return {
                "error": "Amadeus error",
                "details": str(e)
            }
        except ResponseError as e:
            return {
                "error": "Amadeus error",
                "details": e.response.body
            }

    @staticmethod
    def create_flight_order(flight_offer, travelers):
        try:
            client = _get_client()
            payload = {
                "data": {
                    "type": "flight-order",
                    "flightOffers": [flight_offer],
                    "travelers": travelers,
                }
            }
            try:
                # Most SDK versions expect (flight_offer, travelers).
                response = client.booking.flight_orders.post(
                    flight_offer,
                    travelers,
                )
            except TypeError as exc:
                # Fallback for SDKs that expect a payload dict instead.
                if "travelers" in str(exc) or "positional argument" in str(exc):
                    response = client.booking.flight_orders.post(payload)
                else:
                    raise
            return response.data
        except ResponseError as e:
            response = getattr(e, "response", None)
            details = {}
            if response is not None:
                body = getattr(response, "body", None)
                if body:
                    details["body"] = body
                result = getattr(response, "result", None)
                if result:
                    details["result"] = result
                status_code = getattr(response, "status_code", None)
                if status_code is not None:
                    details["status_code"] = status_code
                headers = getattr(response, "headers", None)
                if headers:
                    details["headers"] = headers
                request = getattr(response, "request", None)
                if request is not None:
                    details["request"] = {
                        "path": getattr(request, "path", None),
                        "params": getattr(request, "params", None),
                    }
            if not details:
                details["error"] = str(e)
            details.setdefault("payload_debug", {
                "flight_offer_id": (
                    flight_offer.get("id")
                    if isinstance(flight_offer, dict)
                    else None
                ),
                "traveler_count": len(travelers) if isinstance(travelers, list) else 1,
                "traveler_fields": [
                    sorted(t.keys()) for t in travelers
                    if isinstance(t, dict)
                ] if isinstance(travelers, list) else None,
            })
            logger.error("Amadeus flight order failed: %s", details or str(e))
            raise Exception(details or str(e))
        except RuntimeError as e:
            raise Exception(str(e))
        
    @staticmethod
    def reprice_flight(flight_offer):
        try:
            client = _get_client()
            response = client.shopping.flight_offers.pricing.post({
                "data": {
                    "type": "flight-offers-pricing",
                    "flightOffers": [flight_offer]
                }
            })
            return response.data
        except RuntimeError as e:
            raise Exception(str(e))
        except ResponseError as e:
            body = None
            response = getattr(e, "response", None)
            if response is not None:
                body = getattr(response, "body", None)
            raise Exception(body or str(e))
