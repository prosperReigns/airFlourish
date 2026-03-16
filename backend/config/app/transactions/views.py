from django.utils.decorators import method_decorator
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Transaction
from .serializers import TransactionSerializer
from app.transactions.tasks import process_payment
from django.utils.crypto import get_random_string
from decimal import Decimal

@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_description="List transactions for the authenticated user.",
        responses={200: TransactionSerializer(many=True)},
    ),
)
class UserTransactionListView(generics.ListAPIView):

    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(
            user=self.request.user
        ).order_by("-created_at")
    
@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_description="List all transactions for admin users.",
        responses={200: TransactionSerializer(many=True)},
    ),
)
class AdminTransactionListView(generics.ListAPIView):

    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAdminUser]

    queryset = Transaction.objects.all().order_by("-created_at")

class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Initiate a payment transaction for the authenticated user.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["amount"],
            properties={
                "amount": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                "currency": openapi.Schema(type=openapi.TYPE_STRING, default="NGN"),
                "transaction_type": openapi.Schema(type=openapi.TYPE_STRING, default="flight"),
            },
        ),
        responses={
            200: openapi.Response(
                description="Payment initiated",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "reference": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: "Invalid input data",
        },
    )
    def post(self, request):
        amount = Decimal(request.data.get("amount"))
        currency = request.data.get("currency", "NGN")
        transaction_type = request.data.get("transaction_type", "flight")
        reference = get_random_string(12).upper()
        transaction = Transaction.objects.create(
            user=request.user,
            amount=amount,
            reference=reference,
            currency=currency,
            transaction_type=transaction_type,
            status="pending",
        )

        # Async task
        process_payment.delay(transaction.id)

        return Response({"message": "Payment is being processed", "reference": reference})

class UserTransactionsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List transaction summaries for the authenticated user.",
        responses={
            200: openapi.Response(
                description="Transaction summaries",
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "reference": openapi.Schema(type=openapi.TYPE_STRING),
                            "amount": openapi.Schema(type=openapi.TYPE_STRING),
                            "status": openapi.Schema(type=openapi.TYPE_STRING),
                            "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                        },
                    ),
                ),
            )
        },
    )
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
