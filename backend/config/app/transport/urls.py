from rest_framework.routers import DefaultRouter
from django.urls import path
from app.payments.views import PaymentVerificationView

from .views import AdminTransportViewSet, TransportBookingViewSet, TransportSearchView, TransportViewSet, TransportReservationViewSet,AdminTransportReservationViewSet

router = DefaultRouter()
router.register(r'admin-transports', AdminTransportViewSet, basename='admin-transport')
router.register(r'transport-options', TransportViewSet, basename='transport-options')
router.register(r'transports', TransportBookingViewSet, basename='transport-booking')
router.register(r'transport-reservations', TransportReservationViewSet, basename='transport-reservations')
router.register(r'admin-transport-reservations', AdminTransportReservationViewSet, basename='admin-transport-reservations')

urlpatterns = router.urls + [
    path("search/", TransportSearchView.as_view(), name="transport-search"),
    path("verify-payment/", PaymentVerificationView.as_view(), name="transport-verify-payment"),
]
