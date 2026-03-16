from django.urls import path
from .views import WalletDetailView, WalletLedgerView


urlpatterns = [
    path("wallet/", WalletDetailView.as_view()),
    path("wallet/ledger/", WalletLedgerView.as_view()),
]