from rest_framework.throttling import UserRateThrottle


class HotelSearchThrottle(UserRateThrottle):
    scope = "hotel_search"