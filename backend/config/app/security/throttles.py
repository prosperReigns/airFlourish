from rest_framework.throttling import UserRateThrottle


class LoginThrottle(UserRateThrottle):

    scope = "login"


class PaymentThrottle(UserRateThrottle):

    scope = "payment"


class BookingThrottle(UserRateThrottle):

    scope = "booking"