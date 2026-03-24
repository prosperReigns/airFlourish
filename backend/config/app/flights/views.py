from django.db import transaction
from django.db.models import Case, IntegerField, Q, Value, When
from django.utils.decorators import method_decorator
from django.core.cache import cache
from rest_framework import permissions, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
from app.payments.models import Payment
from app.users.permissions import IsAdminUserType

from app.services.amadeus import AmadeusService
from app.services.booking_engine import BookingEngine
from app.services.flutterwave import FlutterwaveService
from app.services.reference_generator import generate_booking_reference
from app.audit.services import log_action
from app.notifications.services import create_notification
from app.transactions.services import (
    get_or_create_transaction,
    mark_transaction_failed,
    mark_transaction_success,
)
from .models import Airport, FlightBooking
from .serializers import AirportSearchSerializer, AirportSerializer, FlightBookingSerializer
from app.services.flight_transformer import simplify_flight_offers
from app.services.amadeus_transformer import _extract_flight_details
from app.services.helper_function import _convert_amount, _get_user_currency,_quantize_amount,_to_decimal
from app.core.pagination import DefaultPagination
from app.security.throttles import FlightSearchThrottle

@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List flight bookings.",
        responses={200: FlightBookingSerializer(many=True)}
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a flight booking by ID."),
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_description="Create a flight booking (depreciated).",
        request_body=FlightBookingSerializer,
        responses={201: FlightBookingSerializer}
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(operation_description="Update a flight booking.",
        request_body=FlightBookingSerializer,
        responses={200: FlightBookingSerializer}
        ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(operation_description="Partially update a flight booking.",
        request_body=FlightBookingSerializer,
        responses={200: FlightBookingSerializer}
        ),  
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Delete a flight booking.",
        responses={204: "flight booking deleted successfully"}
    ),
)
class FlightBookingViewSet(viewsets.ModelViewSet):
    """ViewSet for managing flight bookings. Regular users can only see and manage their own flight bookings, while admin users can see and manage all flight bookings. This viewset allows users to create new flight bookings by providing the necessary flight details and handles the retrieval, updating, and deletion of flight bookings based on user permissions.
    Expected URL for listing flight bookings: /flight-bookings/
    Expected URL for retrieving a flight booking: /flight-bookings/<booking_id>/
    Expected URL for creating a flight booking: /flight-bookings/
    Expected URL for updating a flight booking: /flight-bookings/<booking_id>/
    Expected URL for deleting a flight booking: /flight-bookings/<booking_id>/
    Expected request data for creating a flight booking:
    {
        "departure_city": "City of departure",
        "arrival_city": "City of arrival",
        "departure_date": "Date of departure",
        "return_date": "Date of return",
        "airline": "Airline name",
        "passengers": 1,
        "flight_offer": { ... },  // Flight offer details from Amadeus
        "travelers": [ ... ],  // Traveler details
        "total_price": 100.00,
        "currency": "USD"
    }
    """
    queryset = FlightBooking.objects.all()
    serializer_class = FlightBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Admin users can see all flight bookings, while regular users can only see their own flight bookings. This method overrides the default queryset to filter the flight bookings based on the user's permissions.
        Expected URL for listing flight bookings: /flight-bookings/
        """
        if getattr(self, 'swagger_fake_view', False):
            return FlightBooking.objects.none()
        user = self.request.user

        # admin sees all bookings
        if getattr(user, "user_type", None) == "admin":
            return FlightBooking.objects.all()

        # Return flights linked to bookings of the logged-in user
        return FlightBooking.objects.filter(booking__user=user)


class AirportViewSet(viewsets.ModelViewSet):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    permission_classes = [IsAuthenticated, IsAdminUserType]

class FlightBookingCache:
    _offer_prefix = "flight_offer:"
    _payment_prefix = "flight_payment_context:"
    _offer_ttl = getattr(settings, "FLIGHT_OFFER_CACHE_TTL", 60 * 60)
    _payment_ttl = getattr(settings, "FLIGHT_PAYMENT_CONTEXT_TTL", 6 * 60 * 60)

    @classmethod
    def store_flight_offer(cls, flight_id, offer):
        if flight_id:
            cache.set(f"{cls._offer_prefix}{flight_id}", offer, timeout=cls._offer_ttl)

    @classmethod
    def get_flight_offer(cls, flight_id):
        if not flight_id:
            return None
        return cache.get(f"{cls._offer_prefix}{flight_id}")

    @classmethod
    def store_payment_context(cls, tx_ref, context):
        if tx_ref:
            cache.set(
                f"{cls._payment_prefix}{tx_ref}",
                context,
                timeout=cls._payment_ttl,
            )

    @classmethod
    def get_payment_context(cls, tx_ref):
        if not tx_ref:
            return {}
        return cache.get(f"{cls._payment_prefix}{tx_ref}") or {}


class SecureFlightBookingView(APIView):
    """Endpoint for securely booking a flight. This view handles the entire process of booking a flight, including repricing the flight offer, initiating payment with Flutterwave, creating a unified booking, and returning a payment link to the frontend. It expects the flight offer and traveler details in the request data, and it ensures that all operations are performed atomically to maintain data integrity.
    Expected request data:
    {
        "flight_offer": { ... },  // Flight offer details from Amadeus
        "travelers": [ ... ],  // Traveler details
        "departure_city": "City of departure",
        "arrival_city": "City of arrival",
        "departure_date": "Date of departure",
        "return_date": "Date of return",
        "airline": "Airline name",
        "passengers": 1
    }
    Expected response data on success:
    {
        "payment_link": "https://flutterwave.com/pay/unique_payment_link",
        "tx_ref": "unique_transaction_reference",
        "booking_id": 1
    }
    Expected response data on failure:
    {
        "error": "Description of the error",
        "details": { ... }  // Additional details about the error
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    @swagger_auto_schema(
        operation_description=(
            "Initiate secure flight booking and return payment link. "
            "Provide `selected_flight_id` from search results or `flight_offer` directly. "
            "Endpoint: /api/flights/secure-book/"
        ),
                         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["travelers"],
            properties={
                "selected_flight_id": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Flight ID returned from search. If provided, cached offer is used.",
                ),
                "flight_offer": openapi.Schema(type=openapi.TYPE_OBJECT, description="Flight offer from Amadeus"),
                "travelers": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
                "departure_city": openapi.Schema(type=openapi.TYPE_STRING),
                "arrival_city": openapi.Schema(type=openapi.TYPE_STRING),
                "departure_date": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                "return_date": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                "airline": openapi.Schema(type=openapi.TYPE_STRING),
                "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                "payment_method": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Optional: card or bank_transfer. Omit to show both on hosted page.",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Payment link created",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "payment_link": openapi.Schema(type=openapi.TYPE_STRING),
                        "tx_ref": openapi.Schema(type=openapi.TYPE_STRING),
                        "booking_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "payment_options": openapi.Schema(type=openapi.TYPE_STRING),
                        "bank_transfer_available": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
            400: "Bad request (missing or invalid data)",
        },
    )
    def post(self, request):
        """Endpoint for securely booking a flight. This view handles the entire process of booking a flight, including repricing the flight offer, initiating payment with Flutterwave, creating a unified booking, and returning a payment link to the frontend. It expects the flight offer and traveler details in the request data, and it ensures that all operations are performed atomically to maintain data integrity.
        Expected request data:
        {
            "flight_offer": { ... },  // Flight offer details from Amadeus
            "travelers": [ ... ],  // Traveler details
            "departure_city": "City of departure",
            "arrival_city": "City of arrival",
            "departure_date": "Date of departure",
            "return_date": "Date of return",
            "airline": "Airline name",
            "passengers": 1
        }
        Expected response data on success:
        {
            "payment_link": "https://flutterwave.com/pay/unique_payment_link",
            "tx_ref": "unique_transaction_reference",
            "booking_id": 1
        }
        Expected response data on failure:
        {
            "error": "Description of the error",
            "details": { ... }  // Additional details about the error
        }
        """
        travelers = request.data.get("travelers", [])
        selected_flight_id = request.data.get("selected_flight_id")
        flight_offer = None

        # Fetch flight offer from cache when available.
        if selected_flight_id:
            flight_offer = FlightBookingCache.get_flight_offer(selected_flight_id)

        payment_method = (request.data.get("payment_method") or "").lower().strip()
        
        if not travelers or not (flight_offer or request.data.get("flight_offer")):
            return Response(
                {"error": "travelers and selected_flight_id or flight_offer are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not flight_offer:
            flight_offer = request.data.get("flight_offer")
            if isinstance(flight_offer, dict):
                raw_offer = flight_offer.get("raw_offer")
                if isinstance(raw_offer, dict):
                    flight_offer = raw_offer

        if payment_method and payment_method not in {"card", "bank_transfer"}:
            return Response(
                {"error": "payment_method must be 'card' or 'bank_transfer'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        def extract_price(offer):
            if not isinstance(offer, dict):
                return None, None
            price = offer.get("price") or {}
            return price.get("total"), price.get("currency")

        base_price, base_currency = extract_price(flight_offer)
        amount = _to_decimal(base_price)
        if not amount or not base_currency:
            return Response(
                {"error": "Unable to determine flight price"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_currency = _get_user_currency(request.user, base_currency)
        target_currency = user_currency

        converted_amount = _convert_amount(amount, base_currency, target_currency)
        conversion_applied = True
        if converted_amount is None:
            converted_amount = amount
            target_currency = base_currency
            conversion_applied = False

        confirmed_price = _quantize_amount(converted_amount)
        currency = target_currency

        if not confirmed_price or not currency:
            return Response(
                {"error": "Unable to determine flight price"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Initiate payment
        tx_ref = generate_booking_reference("pay")
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
            service_type="flight",
            total_price=confirmed_price,
            currency=currency,
        )

        flight_details = _extract_flight_details(flight_offer, travelers)
        meta = {
            "flight_offer": flight_offer,
            "travelers": travelers,
            "original_price": str(base_price),
            "original_currency": base_currency,
            "converted_price": str(confirmed_price),
            "converted_currency": currency,
            "conversion_applied": conversion_applied,
            **flight_details,
        }

        FlightBookingCache.store_payment_context(
            tx_ref,
            {
                "flight_offer": flight_offer,
                "travelers": travelers,
                **flight_details,
            },
        )

        payment_raw_response = {"meta": meta}

        Payment.objects.create(
            booking=booking,
            tx_ref=tx_ref,
            amount=confirmed_price,
            currency=currency,
            payment_method=payment_method or "card",
            status="pending",
            raw_response=payment_raw_response,
        )

        get_or_create_transaction(
            booking=booking,
            reference=tx_ref,
            amount=confirmed_price,
            currency=currency,
        )

        # Return payment link to frontend
        return Response(
            {
                "payment_link": payment_response.get("data", {}).get("link"),
                "tx_ref": tx_ref,
                "booking_id": booking.id,
                "payment_options": payment_options,
                "bank_transfer_available": bank_transfer_available,
            }
        )

class FlightSearchView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [FlightSearchThrottle]

    @swagger_auto_schema(
        operation_description="Search flights via Amadeus. Endpoint: /api/flights/search-flights/",
        manual_parameters=[
            openapi.Parameter("origin", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("destination", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("departure_date", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("return_date", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_STRING),
                        "price": openapi.Schema(type=openapi.TYPE_STRING),
                        "currency": openapi.Schema(type=openapi.TYPE_STRING),
                        "departure": openapi.Schema(type=openapi.TYPE_STRING),
                        "arrival": openapi.Schema(type=openapi.TYPE_STRING),
                        "departure_time": openapi.Schema(type=openapi.TYPE_STRING),
                        "arrival_time": openapi.Schema(type=openapi.TYPE_STRING),
                        "duration": openapi.Schema(type=openapi.TYPE_STRING),
                        "stops": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "airline": openapi.Schema(type=openapi.TYPE_STRING),
                        "raw_offer": openapi.Schema(type=openapi.TYPE_OBJECT),
                        "original_price": openapi.Schema(type=openapi.TYPE_STRING),
                        "original_currency": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: "Missing required query params",
            502: "Upstream error",
        },
    )
    def get(self, request):
        origin = request.GET.get("origin")  # e.g. LOS
        destination = request.GET.get("destination")  # e.g. LHR
        departure_date = request.GET.get("departure_date")
        return_date = request.GET.get("return_date")

        if not origin or not destination or not departure_date:
            return Response(
                {"error": "origin, destination, departure_date required"},
                status=400
            )

        flights = AmadeusService.search_flights(
            origin,
            destination,
            departure_date,
            return_date
        )

        if isinstance(flights, dict) and flights.get("error"):
            return Response(flights, status=status.HTTP_502_BAD_GATEWAY)
        if not isinstance(flights, list):
            return Response(
                {"error": "Unexpected response from Amadeus", "details": flights},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # store pristine raw offers by ID before any transformation
        raw_by_id = {
            offer.get("id"): offer
            for offer in flights
            if isinstance(offer, dict) and offer.get("id")
        }

        simplified = simplify_flight_offers(flights)

        # store each flight in cache by ID
        for offer in simplified:
            flight_id = offer.get("id")
            raw_offer = raw_by_id.get(flight_id)
            if flight_id and raw_offer:
                FlightBookingCache.store_flight_offer(flight_id, raw_offer)

            if not raw_offer:
                continue

            base_price = raw_offer.get("price", {}).get("total")
            base_currency = raw_offer.get("price", {}).get("currency")
            amount = _to_decimal(base_price)
            if not amount or not base_currency:
                continue

            target_currency = _get_user_currency(request.user, base_currency)
            converted_amount = _convert_amount(amount, base_currency, target_currency)
            if converted_amount is None:
                continue

            offer["original_price"] = str(base_price)
            offer["original_currency"] = base_currency
            offer["price"] = str(_quantize_amount(converted_amount))
            offer["currency"] = target_currency
                
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(simplified, request, view=self)
        if page is not None:
            return paginator.get_paginated_response(page)

        return Response(simplified)


class AirportSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        if len(query) < 2:
            return Response([])

        normalized_query = query.lower()
        cache_key = f"airport_search:{normalized_query}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        queryset = (
            Airport.objects.only("code", "city", "name").filter(
                Q(city__icontains=query)
                | Q(name__icontains=query)
                | Q(code__icontains=query)
            )
            .annotate(
                relevance=Case(
                    When(city__icontains=query, then=Value(0)),
                    When(name__icontains=query, then=Value(1)),
                    When(code__icontains=query, then=Value(2)),
                    default=Value(3),
                    output_field=IntegerField(),
                )
            )
            .order_by("relevance", "city", "name")
        )

        limit = getattr(settings, "AIRPORT_SEARCH_LIMIT", 20)
        results = queryset[:limit]
        data = AirportSearchSerializer(results, many=True).data
        cache_timeout = getattr(settings, "AIRPORT_SEARCH_CACHE_TTL", 600)
        cache.set(cache_key, data, timeout=cache_timeout)
        return Response(data)
