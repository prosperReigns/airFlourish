from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, FlightSearchView
from django.urls import path

router = DefaultRouter()
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = router.urls + [
        path('flights/search/', FlightSearchView.as_view(), name='flight-search'),
        ]
