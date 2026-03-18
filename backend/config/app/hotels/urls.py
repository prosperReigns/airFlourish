from rest_framework.routers import DefaultRouter
from django.urls import path
from app.payments.views import PaymentVerificationView
from .views import AdminHotelViewSet, HotelReservationViewSet, HotelViewSet

router = DefaultRouter()
router.register(r'admin-hotels', AdminHotelViewSet, basename='adminhotel')
router.register(r'hotels', HotelViewSet, basename='hotel')
router.register(r'reservation', HotelReservationViewSet, basename='hotelreservation')

urlpatterns = router.urls + [
    # Desired hotel endpoints
    path("hotels/", HotelViewSet.as_view({"get": "list"}), name="hotels-list"),
    path("hotel/<int:pk>/", HotelViewSet.as_view({"get": "retrieve"}), name="hotels-detail"),
    path("book-secure/", HotelReservationViewSet.as_view({"post": "book_secure"}), name="hotel-book-secure"),
    path("reservations/", HotelReservationViewSet.as_view({"get": "list"}), name="hotel-reservations-list"),
    path("reservation/<int:pk>/", HotelReservationViewSet.as_view({"get": "retrieve"}), name="hotel-reservations-detail"),
    path("hotel-reservation/", HotelReservationViewSet.as_view({"post": "reservation"}), name="hotel-reservation-hold"),
    path("checkout/", HotelReservationViewSet.as_view({"post": "checkout"}), name="hotel-reservation-checkout"),
    path("verify-payment/", PaymentVerificationView.as_view(), name="hotel-verify-payment"),
]
