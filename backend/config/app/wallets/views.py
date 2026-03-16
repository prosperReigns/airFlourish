from rest_framework import generics, permissions
from .models import Wallet, LedgerEntry
from .serializers import WalletSerializer, LedgerEntrySerializer


class WalletDetailView(generics.RetrieveAPIView):

    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return Wallet.objects.get(user=self.request.user)


class WalletLedgerView(generics.ListAPIView):

    serializer_class = LedgerEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        wallet = Wallet.objects.get(user=self.request.user)

        return LedgerEntry.objects.filter(wallet=wallet)