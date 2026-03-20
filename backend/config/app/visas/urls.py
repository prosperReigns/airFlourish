from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .views import (
    VisaApplicationViewSet,
    VisaPaymentVerificationView,
    VisaTypeView,
    VisaTypeAdminViewSet,
)

router = SimpleRouter()
router.register(r"applications", VisaApplicationViewSet, basename="visa-application")
router.register(r"admin/visa-types", VisaTypeAdminViewSet, basename="visa-type-admin")

urlpatterns = [
    path("", include(router.urls)),
    path("visa-types/", VisaTypeView.as_view(), name="visa-types"),
    path("payments/verify/", VisaPaymentVerificationView.as_view(), name="visa-payment-verify"),
    path(
        "webhook/payment_verified/",
        VisaPaymentVerificationView.as_view(),
        name="visa-payment-verified-webhook",
    ),
]
