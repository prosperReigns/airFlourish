from rest_framework.routers import DefaultRouter
from .views import (
    PaymentViewSet,
    CardPaymentInitView,
    BankTransferInitView,
    FlutterwaveWebhookView,
    PaymentVerificationView,
    PaymentRedirectView
)
from django.urls import path

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = router.urls + [
    path('card/initiate/', CardPaymentInitView.as_view(), name='card-payment-initiate'),
    path('bank-transfer/initiate/', BankTransferInitView.as_view(), name='bank-transfer-initiate'),
    path('verify/', PaymentVerificationView.as_view(), name='payment-verify'), 
    path('webhook/flutterwave/', FlutterwaveWebhookView.as_view(), name='flutterwave-webhook'),
    path('redirect/', PaymentRedirectView.as_view(), name='payment-redirect'),
]