from amadeus import Client, ResponseError
from django.conf import settings

amadeus = Client(
        client_id=settings.AMADEUS_API_KEY,
        client_secret=settings.AMADEUS_API_SECRET
        )

class AmadeusService:
    @staticmethod
    def search_flights(origin, destination, departure_date, return_date=None):
        try:
            response = amadeus.shopping.flight_offers_search.get(
                 originLocationCode=origin,
                 destinationLocationCode=destination,
                 departureDate=departure_date,
                 returnDate=return_date,
                 adults=1
            )
            return response.data
        except ResponseError as e:
            return {"error": str(e)}

    @staticmethod
    def create_flight_order(flight_offer, travelers):
        try:
            response = amadeus.booking.flight_orders.post({
                "data": {
                    "type": "flight-order",
                    "flightOffers": [flight_offer],
                    "travelers": travelers
                }
            })
            return response.data
        except ResponseError as e:
            raise Exception(str(e))
        
    @staticmethod
    def reprice_flight(flight_offer):
        try:
            response = amadeus.shopping.flight_offers.pricing.post({
                "data": {
                    "type": "flight-offers-pricing",
                    "flightOffers": [flight_offer]
                }
            })
            return response.data
        except ResponseError as e:
            raise Exception(str(e))