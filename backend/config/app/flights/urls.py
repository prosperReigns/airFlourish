from rest_framework.routers import DefaultRouter
from .views import FlightBookingViewSet
from django.urls import path
from .views import SecureFlightBookingView, VerifyFlightPaymentView

router = DefaultRouter()
router.register(r'flights', FlightBookingViewSet, basename='flightbooking')

urlpatterns = router.urls + [
    path("secure-book/", SecureFlightBookingView.as_view()),
    path("verify-payment/", VerifyFlightPaymentView.as_view()),
]
