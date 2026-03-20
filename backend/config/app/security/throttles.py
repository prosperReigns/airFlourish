from rest_framework.throttling import UserRateThrottle


class LoginThrottle(UserRateThrottle):

    scope = "login"


class PaymentThrottle(UserRateThrottle):

    scope = "payment"


class BookingThrottle(UserRateThrottle):

    scope = "booking"


class HotelSearchThrottle(UserRateThrottle):

    scope = "hotel_search"


class FlightSearchThrottle(UserRateThrottle):

    scope = "flight_search"
