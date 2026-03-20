from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

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
from .models import Trip, TransportBooking, TripAssignment
from .permissions import IsAdminOrReadOnlyUserType, IsAdminUserType
from .serializers import (
    TripSerializer,
    TransportBookingSerializer,
    TripAssignmentSerializer,
)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_description="List available trips.",
        responses={200: TripSerializer(many=True)},
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a trip by ID."),
)
class TripViewSet(viewsets.ModelViewSet):
    serializer_class = TripSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnlyUserType]
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Trip.objects.none()
        queryset = Trip.objects.annotate(
            available_seats=F("capacity") - F("booked_seats")
        )
        user = self.request.user
        if getattr(user, "user_type", None) == "admin":
            return queryset
        return queryset.filter(status="scheduled", available_seats__gt=0)


class AdminTripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated, IsAdminUserType]

    @action(detail=True, methods=["post"])
    @transaction.atomic
    @swagger_auto_schema(
        operation_description="Start a trip.",
        responses={200: openapi.Response("Trip started")},
    )
    def start_trip(self, request, pk=None):
        trip = self.get_object()
        trip.status = "en_route"
        trip.save(update_fields=["status"])
        return Response({"status": "Trip started"})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    @swagger_auto_schema(
        operation_description="Complete a trip.",
        responses={200: openapi.Response("Trip completed")},
    )
    def complete_trip(self, request, pk=None):
        trip = self.get_object()
        trip.status = "completed"
        trip.save(update_fields=["status"])
        return Response({"status": "Trip completed"})


class TransportBookingViewSet(viewsets.ModelViewSet):
    serializer_class = TransportBookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return TransportBooking.objects.none()
        user = self.request.user
        queryset = TransportBooking.objects.select_related("trip", "booking")
        if getattr(user, "user_type", None) == "admin":
            return queryset
        return queryset.filter(user=user)

    def _prepare_pricing(self, request, total_price, base_currency):
        amount = _to_decimal(total_price)
        if not amount:
            raise ValueError("Unable to determine trip price")

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
        trip,
        passengers,
        original_price,
        base_currency,
        confirmed_price,
        currency,
        conversion_applied,
        special_requests,
    ):
        return {
            "trip_id": trip.id,
            "trip_name": trip.name,
            "pickup_location": trip.pickup_location,
            "dropoff_location": trip.dropoff_location,
            "departure_time": trip.departure_time.isoformat()
            if trip.departure_time
            else None,
            "passengers": passengers,
            "special_requests": special_requests,
            "original_price": str(original_price),
            "original_currency": base_currency,
            "converted_price": str(confirmed_price),
            "converted_currency": currency,
            "conversion_applied": conversion_applied,
        }

    @transaction.atomic
    @swagger_auto_schema(
        operation_description="Create a transport booking and initiate payment.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["trip", "passengers"],
            properties={
                "trip": openapi.Schema(type=openapi.TYPE_INTEGER),
                "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                "organization": openapi.Schema(type=openapi.TYPE_STRING),
                "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
                "payment_method": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Optional: card or bank_transfer.",
                ),
            },
        ),
        responses={
            201: openapi.Response(
                description="Payment link created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "payment_link": openapi.Schema(type=openapi.TYPE_STRING),
                        "tx_ref": openapi.Schema(type=openapi.TYPE_STRING),
                        "booking_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "transport_booking_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "payment_options": openapi.Schema(type=openapi.TYPE_STRING),
                        "bank_transfer_available": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
            400: "Bad request",
            404: "Trip not found",
        },
    )
    def create(self, request, *args, **kwargs):
        data = request.data
        trip_id = data.get("trip") or data.get("trip_id")
        if not trip_id:
            return Response({"error": "trip is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            passengers = int(data.get("passengers", 1))
        except (TypeError, ValueError):
            return Response(
                {"error": "passengers must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if passengers < 1:
            return Response(
                {"error": "passengers must be at least 1"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_method = (data.get("payment_method") or "").lower().strip()
        if payment_method and payment_method not in {"card", "bank_transfer"}:
            return Response(
                {"error": "payment_method must be 'card' or 'bank_transfer'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        trip = Trip.objects.select_for_update().filter(id=trip_id).first()
        if not trip:
            return Response({"error": "Trip not found"}, status=status.HTTP_404_NOT_FOUND)

        if not trip.is_shared and trip.booked_seats > 0:
            return Response(
                {"error": "Private trip already booked"},
                status=status.HTTP_409_CONFLICT,
            )

        available_seats = trip.capacity - trip.booked_seats
        if available_seats <= 0 or passengers > available_seats:
            return Response(
                {"error": "Not enough available seats"},
                status=status.HTTP_409_CONFLICT,
            )

        price_per_seat = _to_decimal(trip.price_per_seat)
        if not price_per_seat:
            return Response(
                {"error": "Unable to determine trip pricing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base_currency = trip.currency or "NGN"
        total_price = price_per_seat * passengers
        try:
            confirmed_price, currency, conversion_applied = self._prepare_pricing(
                request, total_price, base_currency
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

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
            service_type="transport",
            total_price=confirmed_price,
            currency=currency,
            external_service_id=trip.id,
        )

        transport_booking = TransportBooking.objects.create(
            trip=trip,
            user=request.user,
            booking=booking,
            passengers=passengers,
            organization=data.get("organization"),
            special_requests=data.get("special_requests", ""),
            status="pending",
        )

        trip.booked_seats += passengers
        trip.save(update_fields=["booked_seats"])

        meta = self._build_meta(
            trip,
            passengers,
            total_price,
            base_currency,
            confirmed_price,
            currency,
            conversion_applied,
            data.get("special_requests"),
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
                "transport_booking_id": transport_booking.id,
                "payment_options": payment_options,
                "bank_transfer_available": bank_transfer_available,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    @swagger_auto_schema(
        operation_description="Cancel a transport booking.",
        responses={200: openapi.Response("Booking cancelled")},
    )
    def cancel_booking(self, request, pk=None):
        transport_booking = self.get_object()
        if transport_booking.status == "cancelled":
            return Response({"status": "Booking already cancelled"}, status=status.HTTP_200_OK)

        trip = Trip.objects.select_for_update().get(pk=transport_booking.trip_id)
        transport_booking.status = "cancelled"
        transport_booking.save(update_fields=["status"])

        trip.booked_seats = max(0, trip.booked_seats - transport_booking.passengers)
        trip.save(update_fields=["booked_seats"])

        if transport_booking.booking:
            BookingEngine.cancel_booking(
                transport_booking.booking,
                reason="Transport booking cancelled",
            )

        return Response({"status": "Booking cancelled"})


class TripSearchView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Search trips by pickup, dropoff, and date.",
        manual_parameters=[
            openapi.Parameter("pickup", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("dropoff", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter(
                "date", openapi.IN_QUERY, type=openapi.TYPE_STRING, format="date"
            ),
        ],
        responses={200: TripSerializer(many=True)},
    )
    def get(self, request):
        pickup = request.query_params.get("pickup")
        dropoff = request.query_params.get("dropoff")
        date = request.query_params.get("date")

        trips = Trip.objects.filter(status="scheduled")

        if pickup:
            trips = trips.filter(pickup_location__icontains=pickup)

        if dropoff:
            trips = trips.filter(dropoff_location__icontains=dropoff)

        if date:
            trips = trips.filter(departure_time__date=date)

        trips = trips.annotate(
            available_seats=F("capacity") - F("booked_seats")
        ).filter(available_seats__gt=0)

        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)


class TripAssignmentViewSet(viewsets.ModelViewSet):
    queryset = TripAssignment.objects.all()
    serializer_class = TripAssignmentSerializer
    permission_classes = [IsAuthenticated, IsAdminUserType]
