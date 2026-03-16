from rest_framework import serializers
from .models import Wallet, LedgerEntry


class WalletSerializer(serializers.ModelSerializer):

    class Meta:
        model = Wallet
        fields = [
            "id",
            "balance",
            "currency",
            "created_at",
        ]


class LedgerEntrySerializer(serializers.ModelSerializer):

    class Meta:
        model = LedgerEntry
        fields = [
            "id",
            "entry_type",
            "amount",
            "balance_after",
            "description",
            "created_at",
        ]