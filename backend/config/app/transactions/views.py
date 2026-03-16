from rest_framework import generics, permissions
from .models import Transaction
from .serializers import TransactionSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from app.transactions.tasks import process_payment
from django.utils.crypto import get_random_string
from decimal import Decimal

class UserTransactionListView(generics.ListAPIView):

    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user
        ).order_by("-created_at")
    
class AdminTransactionListView(generics.ListAPIView):

    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAdminUser]

    queryset = Transaction.objects.all().order_by("-created_at")

class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = Decimal(request.data.get("amount"))
        reference = get_random_string(12).upper()
        transaction = Transaction.objects.create(
            user=request.user,
            amount=amount,
            reference=reference,
            status="pending"
        )

        # Async task
        process_payment.delay(transaction.id)

        return Response({"message": "Payment is being processed", "reference": reference})

class UserTransactionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transactions = Transaction.objects.filter(user=request.user)
        data = [
            {
                "reference": t.reference,
                "amount": str(t.amount),
                "status": t.status,
                "created_at": t.created_at
            } for t in transactions
        ]
        return Response(data)