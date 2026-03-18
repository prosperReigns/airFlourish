from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from app.services.booking_engine import BookingEngine
from app.services.flutterwave import FlutterwaveService
from app.services.reference_generator import generate_booking_reference
from app.payments.models import Payment
from app.transactions.services import get_or_create_transaction
from app.pricing.services import convert_currency
from app.pricing.models import ExchangeRate
from .models import Hotel, HotelReservation
from .permissions import IsAdminUserType
from .serializers import HotelReservationSerializer, HotelSerializer
from rest_framework.permissions import IsAuthenticated
from drf_yasg import openapi

def _parse_date(value, field_name):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {field_name} format. Use YYYY-MM-DD")

def _load_hotel_and_dates(data):
    hotel_id = data.get("hotel_id")
    check_in = data.get("check_in")
    check_out = data.get("check_out")
    guests = int(data.get("guests", 1))

    if not hotel_id:
        raise ValueError("hotel_id is required")
    if not check_in or not check_out:
        raise ValueError("check_in and check_out are required")
    if guests < 1:
        raise ValueError("guests must be at least 1")

    hotel = Hotel.objects.filter(id=hotel_id).first()
    if not hotel:
        raise LookupError("Hotel not found")

    check_in_date = _parse_date(check_in, "check_in")
    check_out_date = _parse_date(check_out, "check_out")

    if check_out_date <= check_in_date:
        raise ValueError("check_out must be after check_in")

    if hotel.price_per_night is None:
        raise ValueError("Hotel pricing is not available")

    return hotel, check_in_date, check_out_date, guests

def _calculate_hotel_total(hotel, check_in_date, check_out_date):
    number_of_nights = (check_out_date - check_in_date).days
    total_price = hotel.price_per_night * number_of_nights
    return number_of_nights, total_price

def _get_country_code(user):
    country = getattr(user, "country", None)
    if hasattr(country, "code"):
        return country.code
    if country:
        return str(country)
    return None

def _get_user_currency(user, fallback_currency):
    country_code = _get_country_code(user)
    currency_map = getattr(settings, "COUNTRY_CURRENCY_MAP", {})
    return currency_map.get(country_code, fallback_currency)

def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None

def _quantize_amount(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def _convert_amount(amount, base_currency, target_currency):
    if amount is None:
        return None
    if base_currency == target_currency:
        return amount
    try:
        return convert_currency(amount, base_currency, target_currency)
    except ExchangeRate.DoesNotExist:
        return None

@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List available hotels. Endpoint: /api/hotels/",
                                  manual_parameters=[
                                 openapi.Parameter(
                                     'city', openapi.IN_QUERY, description="Filter hotels by city", type=openapi.TYPE_STRING
                                 ),
                                 openapi.Parameter(
                                     'check_in', openapi.IN_QUERY, description="Filter hotels available for check-in date (YYYY-MM-DD)", type=openapi.TYPE_STRING
                                 ),
                                 openapi.Parameter(
                                     'check_out', openapi.IN_QUERY, description="Filter hotels available for check-out date (YYYY-MM-DD)", type=openapi.TYPE_STRING
                                 ),
                                 openapi.Parameter(
                                     'guests', openapi.IN_QUERY, description="Filter hotels that can accommodate the specified number of guests", type=openapi.TYPE_INTEGER
                                 ),
                             ]
    )
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a hotel by ID. Endpoint: /api/hotels/hotel/{id}/",
                                  manual_parameters=[
                                 openapi.Parameter(
                                     'id', openapi.IN_PATH, description="The ID of the hotel to retrieve", type=openapi.TYPE_INTEGER
                                 ),
                             ]
    )
)
class HotelViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for listing and retrieving hotels. Both regular users and admin users can access this viewset, but only read operations are allowed.
    Expected URL for listing hotels: /hotels/
    Expected URL for retrieving a hotel: /hotels/<hotel_id>/
    """
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    permission_classes = [permissions.IsAuthenticated]


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List hotel reservations. Endpoint: /api/hotels/reservations/",
                                  manual_parameters=[
                                 openapi.Parameter(
                                     'hotel_id', openapi.IN_QUERY, description="Filter reservations by hotel ID", type=openapi.TYPE_INTEGER
                                 ),
                             ]
    )
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a hotel reservation by ID. Endpoint: /api/hotels/reservation/{id}/",
                                  manual_parameters=[
                                 openapi.Parameter(
                                     'id', openapi.IN_PATH, description="The ID of the hotel reservation to retrieve", type=openapi.TYPE_INTEGER
                                 ),
                             ]
    )
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_description="Create a hotel booking with payment (legacy). Endpoint: /api/hotels/book-secure/",
                                  request_body=openapi.Schema(
                                      type=openapi.TYPE_OBJECT,
                                      required=["hotel_id", "check_in", "check_out"],
                                      properties={
                                          "hotel_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                          "check_in": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                          "check_out": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                          "guests": openapi.Schema(type=openapi.TYPE_INTEGER),
                                          "payment_method": openapi.Schema(
                                              type=openapi.TYPE_STRING,
                                              description="Optional: card or bank_transfer",
                                          ),
                                      },
                                  ),
                                  responses={
                                 201: openapi.Response(
                                     description="Hotel reservation created successfully",
                                     schema=openapi.Schema(
                                         type=openapi.TYPE_OBJECT,
                                         properties={
                                             "payment_link": openapi.Schema(type=openapi.TYPE_STRING),
                                             "tx_ref": openapi.Schema(type=openapi.TYPE_STRING),
                                             "booking_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                             "reservation_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                             "payment_options": openapi.Schema(type=openapi.TYPE_STRING),
                                             "bank_transfer_available": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                         }
                                     )
                                 ),
                                 400: "Invalid input data"
                             }
    )
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(operation_description="Update a hotel reservation.",
                                  request_body=HotelReservationSerializer,
                                  responses={
                                      200: openapi.Response(
                                          description="Hotel reservation updated successfully",
                                          schema=openapi.Schema(
                                              type=openapi.TYPE_OBJECT,
                                              properties={
                                                  "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "hotel_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "check_in": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                                  "check_out": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                              }
                                          )
                                      ),
                                      400: "Invalid input data"
                                  }
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(operation_description="Partially update a hotel reservation.",
                                  request_body=HotelReservationSerializer,
                                    responses={
                                        200: openapi.Response(
                                            description="Hotel reservation updated successfully",
                                            schema=openapi.Schema(
                                                type=openapi.TYPE_OBJECT,
                                                properties={
                                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                    "hotel_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                    "check_in": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                                    "check_out": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                                }
                                            )
                                        ),
                                        400: "Invalid input data"
                                    }
                                ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Delete a hotel reservation.",
                                  responses={
                                      204: "Hotel reservation deleted successfully",
                                      404: "Hotel reservation not found"
                                  }
                                ),
)
class HotelReservationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing hotel reservations. Regular users can only see and manage their own reservations, while admin users can see and manage all reservations.
    Expected URL for creating a reservation: /hotel-reservations/
    Expected request data for creating a reservation:
    {
        "hotel_id": 1,
        "check_in": "2023-10-01",
        "check_out": "2023-10-05",
        "guests": 2
    }
    """

    queryset = HotelReservation.objects.all()
    serializer_class = HotelReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Admin users can see all reservations, regular users can only see their own reservations."""
        if getattr(self, 'swagger_fake_view', False):
            return HotelReservation.objects.none()
        user = self.request.user
        if getattr(user, "user_type", None) == "admin":
            return HotelReservation.objects.all()
        return HotelReservation.objects.filter(booking__user=user)

    def _prepare_pricing(self, request, total_price, base_currency):
        amount = _to_decimal(total_price)
        if not amount:
            raise ValueError("Unable to determine hotel price")

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
        hotel,
        check_in_date,
        check_out_date,
        guests,
        total_price,
        base_currency,
        confirmed_price,
        currency,
        conversion_applied,
    ):
        return {
            "hotel_id": hotel.id,
            "hotel_name": hotel.hotel_name,
            "check_in": str(check_in_date),
            "check_out": str(check_out_date),
            "guests": guests,
            "original_price": str(total_price),
            "original_currency": base_currency,
            "converted_price": str(confirmed_price),
            "converted_currency": currency,
            "conversion_applied": conversion_applied,
        }

    def _create_reservation(self, request):
        data = request.data
        if not request.headers.get("Idempotency-Key"):
            return Response(
                {"error": "Idempotency-Key header required for reservation holds"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            hotel, check_in_date, check_out_date, guests = _load_hotel_and_dates(data)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except LookupError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        number_of_nights, total_price = _calculate_hotel_total(
            hotel, check_in_date, check_out_date
        )

        base_currency = hotel.currency or "NGN"
        try:
            confirmed_price, currency, conversion_applied = self._prepare_pricing(
                request, total_price, base_currency
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        booking = BookingEngine.create_booking(
            user=request.user,
            service_type="hotel",
            total_price=confirmed_price,
            currency=currency,
            external_service_id=hotel.id,
        )

        hold_minutes = getattr(settings, "HOTEL_RESERVATION_HOLD_MINUTES", 30)
        hold_expires_at = timezone.now() + timedelta(minutes=hold_minutes)

        reservation = HotelReservation.objects.create(
            user=request.user,
            booking=booking,
            hotel_name=hotel.hotel_name,
            check_in=check_in_date,
            check_out=check_out_date,
            guests=guests,
            total_price=confirmed_price,
            hold_expires_at=hold_expires_at,
        )

        meta = self._build_meta(
            hotel,
            check_in_date,
            check_out_date,
            guests,
            total_price,
            base_currency,
            confirmed_price,
            currency,
            conversion_applied,
        )

        return Response(
            {
                "message": "Reservation created",
                "booking_id": booking.id,
                "reservation_id": reservation.id,
                "currency": currency,
                "total_price": str(confirmed_price),
                "hold_expires_at": hold_expires_at.isoformat(),
                "meta": meta,
            },
            status=status.HTTP_201_CREATED,
        )

    def _create_secure_booking(self, request):
        data = request.data
        payment_method = (data.get("payment_method") or "").lower().strip()
        if payment_method and payment_method not in {"card", "bank_transfer"}:
            return Response(
                {"error": "payment_method must be 'card' or 'bank_transfer'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            hotel, check_in_date, check_out_date, guests = _load_hotel_and_dates(data)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except LookupError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        number_of_nights, total_price = _calculate_hotel_total(
            hotel, check_in_date, check_out_date
        )

        base_currency = hotel.currency or "NGN"
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
            service_type="hotel",
            total_price=confirmed_price,
            currency=currency,
            external_service_id=hotel.id,
        )

        reservation = HotelReservation.objects.create(
            user=request.user,
            booking=booking,
            hotel_name=hotel.hotel_name,
            check_in=check_in_date,
            check_out=check_out_date,
            guests=guests,
            total_price=confirmed_price,
        )

        meta = self._build_meta(
            hotel,
            check_in_date,
            check_out_date,
            guests,
            total_price,
            base_currency,
            confirmed_price,
            currency,
            conversion_applied,
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
                "reservation_id": reservation.id,
                "payment_options": payment_options,
                "bank_transfer_available": bank_transfer_available,
            },
            status=status.HTTP_201_CREATED,
        )

    def _checkout_reservation(self, request):
        data = request.data
        if not request.headers.get("Idempotency-Key"):
            return Response(
                {"error": "Idempotency-Key header required for checkout"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reservation_id = data.get("reservation_id")
        if not reservation_id:
            return Response(
                {"error": "reservation_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reservation = (
            HotelReservation.objects.select_related("booking")
            .filter(id=reservation_id, booking__user=request.user)
            .first()
        )
        if not reservation:
            return Response({"error": "Reservation not found"}, status=status.HTTP_404_NOT_FOUND)

        if reservation.status != "pending":
            return Response(
                {"error": "Reservation is not pending"},
                status=status.HTTP_409_CONFLICT,
            )

        if reservation.hold_expires_at and reservation.hold_expires_at <= timezone.now():
            return Response(
                {"error": "Reservation hold has expired"},
                status=status.HTTP_409_CONFLICT,
            )

        if reservation.hold_expires_at:
            hold_minutes = getattr(settings, "HOTEL_RESERVATION_HOLD_MINUTES", 30)
            reservation.hold_expires_at = timezone.now() + timedelta(minutes=hold_minutes)
            reservation.save(update_fields=["hold_expires_at"])

        booking = reservation.booking
        confirmed_price = _to_decimal(booking.total_price)
        if not confirmed_price:
            return Response(
                {"error": "Unable to determine reservation price"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        currency = booking.currency or "NGN"

        payment_method = (data.get("payment_method") or "").lower().strip()
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

        meta = {
            "reservation_id": reservation.id,
            "hotel_name": reservation.hotel_name,
            "check_in": str(reservation.check_in),
            "check_out": str(reservation.check_out),
            "guests": reservation.guests,
            "converted_price": str(confirmed_price),
            "converted_currency": currency,
        }

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
                "reservation_id": reservation.id,
                "payment_options": payment_options,
                "bank_transfer_available": bank_transfer_available,
            },
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Legacy create -> secure booking with payment."""
        return self._create_secure_booking(request)

    @action(detail=False, methods=["post"], url_path="book-secure")
    @swagger_auto_schema(
        operation_description="Create a hotel booking with payment. Endpoint: /api/hotels/book-secure/",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["hotel_id", "check_in", "check_out"],
            properties={
                "hotel_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "check_in": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                "check_out": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                "guests": openapi.Schema(type=openapi.TYPE_INTEGER),
                "payment_method": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Optional: card or bank_transfer",
                ),
            },
        ),
        responses={
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "payment_link": openapi.Schema(type=openapi.TYPE_STRING),
                    "tx_ref": openapi.Schema(type=openapi.TYPE_STRING),
                    "booking_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "reservation_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "payment_options": openapi.Schema(type=openapi.TYPE_STRING),
                    "bank_transfer_available": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                },
            )
        },
    )
    def book_secure(self, request):
        return self._create_secure_booking(request)

    @action(detail=False, methods=["post"], url_path="reservation")
    @swagger_auto_schema(
        operation_description="Create a hotel reservation without payment. Endpoint: /api/hotels/hotel-reservation/",
        manual_parameters=[
            openapi.Parameter(
                "Idempotency-Key",
                openapi.IN_HEADER,
                description="Required to avoid duplicate reservation holds.",
                type=openapi.TYPE_STRING,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["hotel_id", "check_in", "check_out"],
            properties={
                "hotel_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "check_in": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                "check_out": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                "guests": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "message": openapi.Schema(type=openapi.TYPE_STRING),
                    "booking_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "reservation_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "currency": openapi.Schema(type=openapi.TYPE_STRING),
                    "total_price": openapi.Schema(type=openapi.TYPE_STRING),
                    "hold_expires_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
                },
            )
        },
    )
    def reservation(self, request):
        return self._create_reservation(request)

    @action(detail=False, methods=["post"], url_path="checkout")
    @swagger_auto_schema(
        operation_description="Pay for an existing hotel reservation. Endpoint: /api/hotels/checkout/",
        manual_parameters=[
            openapi.Parameter(
                "Idempotency-Key",
                openapi.IN_HEADER,
                description="Required to avoid duplicate payments.",
                type=openapi.TYPE_STRING,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["reservation_id"],
            properties={
                "reservation_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "payment_method": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Optional: card or bank_transfer",
                ),
            },
        ),
        responses={
            201: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "payment_link": openapi.Schema(type=openapi.TYPE_STRING),
                    "tx_ref": openapi.Schema(type=openapi.TYPE_STRING),
                    "booking_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "reservation_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    "payment_options": openapi.Schema(type=openapi.TYPE_STRING),
                    "bank_transfer_available": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                },
            )
        },
    )
    def checkout(self, request):
        return self._checkout_reservation(request)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List hotels (admin).",
                                  manual_parameters=[
                                 openapi.Parameter(
                                     'city', openapi.IN_QUERY, description="Filter hotels by city", type=openapi.TYPE_STRING
                                 ),
                                 openapi.Parameter(
                                     'country', openapi.IN_QUERY, description="Filter hotels by country", type=openapi.TYPE_STRING
                                 ),
                             ]
    )
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a hotel by ID (admin).",
                                  manual_parameters=[
                                 openapi.Parameter(
                                     'id', openapi.IN_PATH, description="The ID of the hotel to retrieve", type=openapi.TYPE_INTEGER
                                 ),
                             ]
    )
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(operation_description="Create a hotel (admin).",
                                  request_body=HotelSerializer,
                                  responses={
                                 201: openapi.Response(
                                     description="Hotel created successfully",
                                     schema=openapi.Schema(
                                         type=openapi.TYPE_OBJECT,
                                         properties={
                                             "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                             "hotel_name": openapi.Schema(type=openapi.TYPE_STRING),
                                             "city": openapi.Schema(type=openapi.TYPE_STRING),
                                             "address": openapi.Schema(type=openapi.TYPE_STRING),
                                             "country": openapi.Schema(type=openapi.TYPE_STRING),
                                             "price_per_night": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                                             "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                             "available_rooms": openapi.Schema(type=openapi.TYPE_INTEGER),
                                             "description": openapi.Schema(type=openapi.TYPE_STRING),
                                             "facilities": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                             "images": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                         }
                                     )
                                 ),
                                 400: "Invalid input data"
                             }
    )
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(operation_description="Update a hotel (admin).",
                                  request_body=HotelSerializer,
                                  responses={
                                      200: openapi.Response(
                                          description="Hotel updated successfully",
                                          schema=openapi.Schema(
                                              type=openapi.TYPE_OBJECT,
                                              properties={
                                                  "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "hotel_name": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "city": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "address": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "country": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "price_per_night": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                                                  "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "available_rooms": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "description": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "facilities": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                  "images": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                              }
                                          )
                                      ),
                                      400: "Invalid input data"
                                  }
                                ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(operation_description="Partially update a hotel (admin).",
                                  request_body=HotelSerializer,
                                  responses={
                                      200: openapi.Response(
                                          description="Hotel updated successfully",
                                          schema=openapi.Schema(
                                              type=openapi.TYPE_OBJECT,
                                              properties={
                                                  "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "hotel_name": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "city": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "address": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "country": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "price_per_night": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                                                  "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "available_rooms": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "description": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "facilities": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                  "images": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                              }
                                          )
                                      ),
                                      400: "Invalid input data"
                                  }
                                ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Delete a hotel (admin).",
                                  responses={
                                      204: "Hotel deleted successfully",
                                      404: "Hotel not found"
                                  }
                                ),
)
class AdminHotelViewSet(viewsets.ModelViewSet):
    """This viewset is for admin users to manage hotels. It includes additional endpoints for backward compatibility with some clients.
    Only users with user_type 'admin' can access this viewset."""
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUserType]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    # Backward-compatible endpoints used by some clients
    # /hotels/create_hotel/
    @action(detail=False, methods=["post"], url_path="create_hotel")
    @swagger_auto_schema(operation_description="Create a hotel (legacy admin endpoint).",
                             request_body=HotelSerializer,
                             responses={
                                 201: openapi.Response(
                                        description="Hotel created successfully",
                                        schema=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                "hotel_name": openapi.Schema(type=openapi.TYPE_STRING),
                                                "city": openapi.Schema(type=openapi.TYPE_STRING),
                                                "address": openapi.Schema(type=openapi.TYPE_STRING),
                                                "country": openapi.Schema(type=openapi.TYPE_STRING),
                                                "price_per_night": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                                                "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                "available_rooms": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                "description": openapi.Schema(type=openapi.TYPE_STRING),
                                                "facilities": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                "images": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                            }
                                        )
                                    ),
                                 400: "Invalid input data"
                                }
                            )
    def create_hotel(self, request):
        """Expected request data:
        {
            "hotel_name": "Hotel ABC",
            "city": "Lagos",
            "address": "123 Main St",
            "country": "NG",
            "price_per_night": 10000.00,
            "currency": "NGN",
            "available_rooms": 10,
            "description": "A nice hotel in Lagos",
            "facilities": ["Free WiFi", "Pool", "Gym"],
            "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
        }"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # /hotels/get_hotel/<hotel_id>/
    @action(detail=False, methods=["get"], url_path="get_hotel/(?P<hotel_id>[^/.]+)")
    @swagger_auto_schema(operation_description="Retrieve a hotel by ID (legacy admin endpoint).",
                             manual_parameters=[
                                 openapi.Parameter(
                                     'hotel_id', openapi.IN_PATH, description="The ID of the hotel to retrieve", type=openapi.TYPE_INTEGER
                                 ),
                             ],
                             responses={
                                 200: openapi.Response(
                                        description="Hotel retrieved successfully",
                                        schema=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                "hotel_name": openapi.Schema(type=openapi.TYPE_STRING),
                                                "city": openapi.Schema(type=openapi.TYPE_STRING),
                                                "address": openapi.Schema(type=openapi.TYPE_STRING),
                                                "country": openapi.Schema(type=openapi.TYPE_STRING),
                                                "price_per_night": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                                                "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                "available_rooms": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                "description": openapi.Schema(type=openapi.TYPE_STRING),
                                                "facilities": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                "images": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                            }
                                        )
                                    ),
                                 404: "Hotel not found"
                                }
                            )
    def get_hotel(self, request, hotel_id=None):
        """Expected URL: /hotels/get_hotel/1/
        This endpoint is used by some clients that expect a specific URL for fetching a hotel by ID.
        """
        hotel = self.get_queryset().filter(id=hotel_id).first()
        if not hotel:
            return Response({"error": "Hotel not found"}, status=404)
        serializer = self.get_serializer(hotel)
        return Response(serializer.data)

    # /hotels/get_all_hotels/
    @action(detail=False, methods=["get"], url_path="get_all_hotels")
    @swagger_auto_schema(operation_description="List all hotels (legacy admin endpoint).",
                             responses={
                                 200: openapi.Response(
                                        description="List of hotels retrieved successfully",
                                        schema=openapi.Schema(
                                            type=openapi.TYPE_ARRAY,
                                            items=openapi.Schema(
                                                type=openapi.TYPE_OBJECT,
                                                properties={
                                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                    "hotel_name": openapi.Schema(type=openapi.TYPE_STRING),
                                                    "city": openapi.Schema(type=openapi.TYPE_STRING),
                                                    "address": openapi.Schema(type=openapi.TYPE_STRING),
                                                    "country": openapi.Schema(type=openapi.TYPE_STRING),
                                                    "price_per_night": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                                                    "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                    "available_rooms": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                    "description": openapi.Schema(type=openapi.TYPE_STRING),
                                                    "facilities": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                    "images": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                }
                                            )
                                        )
                                    ),
                             }
    )
    def get_all_hotels(self, request):
        """Expected URL: /hotels/get_all_hotels/
        This endpoint is used by some clients that expect a specific URL for fetching all hotels.
        """
        hotels = self.get_queryset()
        serializer = self.get_serializer(hotels, many=True)
        return Response(serializer.data)
