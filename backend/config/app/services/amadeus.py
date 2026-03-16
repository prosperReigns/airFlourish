from amadeus import Client, ResponseError
from django.conf import settings

_amadeus_client = None


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
            response = client.shopping.flight_offers_search.get(
                 originLocationCode=origin,
                 destinationLocationCode=destination,
                 departureDate=departure_date,
                 returnDate=return_date,
                 adults=1
            )
            return response.data
        except RuntimeError as e:
            return {"error": str(e)}
        except ResponseError as e:
            return {"error": str(e)}

    @staticmethod
    def create_flight_order(flight_offer, travelers):
        try:
            client = _get_client()
            response = client.booking.flight_orders.post({
                "data": {
                    "type": "flight-order",
                    "flightOffers": [flight_offer],
                    "travelers": travelers
                }
            })
            return response.data
        except RuntimeError as e:
            raise Exception(str(e))
        except ResponseError as e:
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
            raise Exception(str(e))
