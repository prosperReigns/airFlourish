from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import VisaApplicationViewSet, VisaPaymentVerificationView

router = SimpleRouter()
router.register(r"applications", VisaApplicationViewSet, basename="visa-application")

urlpatterns = [
    path("", include(router.urls)),
    path("payments/verify/", VisaPaymentVerificationView.as_view(), name="visa-payment-verify"),
]
