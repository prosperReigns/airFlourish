from django.utils.decorators import method_decorator
from rest_framework import generics, permissions
from drf_yasg.utils import swagger_auto_schema

from .models import Wallet, LedgerEntry
from .serializers import WalletSerializer, LedgerEntrySerializer


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_description="Retrieve the authenticated user's wallet details.",
        responses={200: WalletSerializer()},
    ),
)
class WalletDetailView(generics.RetrieveAPIView):

    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        if getattr(self, "swagger_fake_view", False):
            return Wallet(balance=0, currency="USD")
        return Wallet.objects.get(user=self.request.user)


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_description="List ledger entries for the authenticated user's wallet.",
        responses={200: LedgerEntrySerializer(many=True)},
    ),
)
class WalletLedgerView(generics.ListAPIView):

    serializer_class = LedgerEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        wallet = Wallet.objects.get(user=self.request.user)

        return LedgerEntry.objects.filter(wallet=wallet)
