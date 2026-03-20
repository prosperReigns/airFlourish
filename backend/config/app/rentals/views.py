import math

from django.conf import settings
from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from app.payments.models import Payment
from app.services.booking_engine import BookingEngine
from app.services.flutterwave import FlutterwaveService
from app.services.helper_function import (
    _convert_amount,
    _get_user_currency,
    _quantize_amount,
    _to_decimal,
)
from app.services.reference_generator import generate_booking_reference
from app.transactions.services import get_or_create_transaction
from .models import CarRental
from .serializers import CarRentalSerializer


class CarRentalViewSet(viewsets.ModelViewSet):
    serializer_class = CarRentalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return CarRental.objects.none()
        user = self.request.user
        queryset = CarRental.objects.select_related("vehicle", "booking")
        if getattr(user, "user_type", None) == "admin":
            return queryset
        return queryset.filter(user=user)

    def _calculate_total_price(self, start_date, end_date, daily_rate):
        duration_seconds = (end_date - start_date).total_seconds()
        if duration_seconds <= 0:
            raise ValueError("End date must be after start date")
        days = math.ceil(duration_seconds / 86400)
        return daily_rate * days, days

    def _prepare_pricing(self, request, total_price, base_currency):
        amount = _to_decimal(total_price)
        if not amount:
            raise ValueError("Unable to determine rental price")

        target_currency = _get_user_currency(request.user, base_currency)
        converted_amount = _convert_amount(amount, base_currency, target_currency)
        conversion_applied = True
        if converted_amount is None:
            converted_amount = amount
            target_currency = base_currency
            conversion_applied = False

        confirmed_price = _quantize_amount(converted_amount)
        return confirmed_price, target_currency, conversion_applied

    def _build_meta(
        self,
        rental,
        total_price,
        base_currency,
        confirmed_price,
        currency,
        conversion_applied,
        rental_days,
    ):
        return {
            "rental_id": rental.id,
            "vehicle_id": rental.vehicle_id,
            "start_date": rental.start_date.isoformat(),
            "end_date": rental.end_date.isoformat(),
            "days": rental_days,
            "original_price": str(total_price),
            "original_currency": base_currency,
            "converted_price": str(confirmed_price),
            "converted_currency": currency,
            "conversion_applied": conversion_applied,
        }

    @transaction.atomic
    @swagger_auto_schema(
        operation_description="Create a car rental and initiate payment.",
        request_body=CarRentalSerializer,
        responses={
            201: openapi.Response(
                description="Payment link created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "payment_link": openapi.Schema(type=openapi.TYPE_STRING),
                        "tx_ref": openapi.Schema(type=openapi.TYPE_STRING),
                        "booking_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "rental_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "payment_options": openapi.Schema(type=openapi.TYPE_STRING),
                        "bank_transfer_available": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
            400: "Bad request",
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        daily_rate = _to_decimal(data.get("daily_rate"))
        if not daily_rate:
            return Response(
                {"error": "Unable to determine daily rate"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            total_price, rental_days = self._calculate_total_price(
                data["start_date"], data["end_date"], daily_rate
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        base_currency = (request.data.get("currency") or "NGN").upper()

        try:
            confirmed_price, currency, conversion_applied = self._prepare_pricing(
                request, total_price, base_currency
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payment_method = (request.data.get("payment_method") or "").lower().strip()
        if payment_method and payment_method not in {"card", "bank_transfer"}:
            return Response(
                {"error": "payment_method must be 'card' or 'bank_transfer'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        supported_bank_currencies = set(
            getattr(settings, "BANK_TRANSFER_SUPPORTED_CURRENCIES", ["NGN"])
        )
        bank_transfer_available = currency in supported_bank_currencies

        payment_options = "card,banktransfer"
        if not bank_transfer_available:
            payment_options = "card"
        if payment_method == "card":
            payment_options = "card"
        elif payment_method == "bank_transfer":
            payment_options = "banktransfer" if bank_transfer_available else "card"

        tx_ref = generate_booking_reference("pay")
        payment_response = FlutterwaveService().initiate_card_payment(
            amount=confirmed_price,
            currency=currency,
            customer_email=request.user.email,
            tx_ref=tx_ref,
            payment_options=payment_options,
        )
        if payment_response.get("status") == "error":
            return Response(
                {"error": "Payment initiation failed", "details": payment_response.get("message")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking = BookingEngine.create_booking(
            user=request.user,
            service_type="rental",
            total_price=confirmed_price,
            currency=currency,
            external_service_id=data["vehicle"].id,
        )

        rental = CarRental.objects.create(
            vehicle=data["vehicle"],
            user=request.user,
            booking=booking,
            start_date=data["start_date"],
            end_date=data["end_date"],
            daily_rate=daily_rate,
            total_price=confirmed_price,
            pickup_location=data.get("pickup_location"),
            dropoff_location=data.get("dropoff_location"),
            deposit_amount=data.get("deposit_amount"),
            status="pending",
        )

        meta = self._build_meta(
            rental,
            total_price,
            base_currency,
            confirmed_price,
            currency,
            conversion_applied,
            rental_days,
        )

        Payment.objects.create(
            booking=booking,
            tx_ref=tx_ref,
            amount=confirmed_price,
            currency=currency,
            payment_method=payment_method or "card",
            status="pending",
            raw_response={"meta": meta},
        )

        get_or_create_transaction(
            booking=booking,
            reference=tx_ref,
            amount=confirmed_price,
            currency=currency,
        )

        return Response(
            {
                "payment_link": payment_response.get("data", {}).get("link"),
                "tx_ref": tx_ref,
                "booking_id": booking.id,
                "rental_id": rental.id,
                "payment_options": payment_options,
                "bank_transfer_available": bank_transfer_available,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    @swagger_auto_schema(
        operation_description="Cancel a car rental.",
        responses={200: openapi.Response("Rental cancelled")},
    )
    def cancel_reservation(self, request, pk=None):
        rental = self.get_object()
        if rental.status == "cancelled":
            return Response({"status": "Rental already cancelled"}, status=status.HTTP_200_OK)

        rental.status = "cancelled"
        rental.save(update_fields=["status"])

        if rental.booking:
            BookingEngine.cancel_booking(rental.booking, reason="Car rental cancelled")

        return Response({"status": "Rental cancelled"})
