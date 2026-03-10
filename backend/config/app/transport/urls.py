from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import AdminTransportViewSet, TransportBookingViewSet, TransportSearchView, TransportViewSet

router = DefaultRouter()
router.register(r'admin-transports', AdminTransportViewSet, basename='admin-transport')
router.register(r'transport-options', TransportViewSet, basename='transport-options')
router.register(r'transports', TransportBookingViewSet, basename='transport-booking')

urlpatterns = router.urls + [
    path("search/", TransportSearchView.as_view(), name="transport-search"),
]
