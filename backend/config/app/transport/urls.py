from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import (
    TripViewSet,
    AdminTripViewSet,
    TransportBookingViewSet,
    TripSearchView,
    TripAssignmentViewSet,
)

router = DefaultRouter()

# USER ROUTES
router.register(r"trips", TripViewSet, basename="trips")
router.register(r"bookings", TransportBookingViewSet, basename="transport-bookings")

# ADMIN ROUTES
router.register(r"admin/trips", AdminTripViewSet, basename="admin-trips")
router.register(r"admin/assignments", TripAssignmentViewSet, basename="assignments")

urlpatterns = router.urls + [
    path("trips/search/", TripSearchView.as_view(), name="trip-search"),
]