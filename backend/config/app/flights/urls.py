from rest_framework.routers import DefaultRouter
from .views import FlightBookingViewSet
from django.urls import path
from .views import SecureFlightBookingView, FlightSearchView

router = DefaultRouter()
router.register(r'flights', FlightBookingViewSet, basename='flightbooking')

urlpatterns = router.urls + [
    path("secure-book/", SecureFlightBookingView.as_view()),
    path("search-flights/", FlightSearchView.as_view(), name="search-flights"),
]
