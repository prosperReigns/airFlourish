from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from rest_framework import permissions, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from app.payments.models import Payment
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
from .models import FlightBooking
from .serializers import FlightBookingSerializer

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
        operation_description="Create a flight booking.",
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

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Expected request data:
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
        flight_offer = request.data.get("flight_offer")
        travelers = request.data.get("travelers")
        total_price = request.data.get("total_price")
        currency = request.data.get("currency", "NGN")

        if not flight_offer or not travelers:
            return Response(
                {"error": "flight_offer and travelers are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Book with Amadeus + Create unified booking
        booking, _amadeus_response = BookingEngine.book_flight(
            user=request.user,
            flight_offer=flight_offer,
            travelers=travelers,
            total_price=total_price,
            currency=currency,
        )

        # Create FlightBooking record
        flight_booking = FlightBooking.objects.create(
            booking=booking,
            departure_city=request.data["departure_city"],
            arrival_city=request.data["arrival_city"],
            departure_date=request.data["departure_date"],
            return_date=request.data.get("return_date"),
            airline=request.data["airline"],
            passengers=request.data.get("passengers", 1),
        )

        serializer = self.get_serializer(flight_booking)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
    @swagger_auto_schema(operation_description="Initiate secure flight booking and return payment link.",
                         request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["flight_offer", "travelers", "departure_city", "arrival_city", "departure_date", "airline"],
            properties={
                "flight_offer": openapi.Schema(type=openapi.TYPE_OBJECT, description="Flight offer from Amadeus"),
                "travelers": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
                "departure_city": openapi.Schema(type=openapi.TYPE_STRING),
                "arrival_city": openapi.Schema(type=openapi.TYPE_STRING),
                "departure_date": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                "return_date": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                "airline": openapi.Schema(type=openapi.TYPE_STRING),
                "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
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
        flight_offer = request.data.get("flight_offer")
        travelers = request.data.get("travelers")
        if not flight_offer or not travelers:
            return Response(
                {"error": "flight_offer and travelers are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reprice flight
        priced_offer = AmadeusService.reprice_flight(flight_offer)
        try:
            confirmed_price = priced_offer["flightOffers"][0]["price"]["total"]
            currency = priced_offer["flightOffers"][0]["price"]["currency"]
        except (KeyError, IndexError, TypeError):
            return Response(
                {"error": "Unable to reprice flight"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Initiate payment
        tx_ref = generate_booking_reference("pay")
        payment_response = FlutterwaveService().initiate_card_payment(
            amount=confirmed_price,
            currency=currency,
            customer_email=request.user.email,
            tx_ref=tx_ref,
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

        meta = {
            "flight_offer": flight_offer,
            "travelers": travelers,
            "departure_city": request.data.get("departure_city"),
            "arrival_city": request.data.get("arrival_city"),
            "departure_date": request.data.get("departure_date"),
            "return_date": request.data.get("return_date"),
            "airline": request.data.get("airline"),
            "passengers": request.data.get("passengers"),
        }

        Payment.objects.create(
            booking=booking,
            tx_ref=tx_ref,
            amount=confirmed_price,
            currency=currency,
            payment_method="card",
            status="pending",
            raw_response={"meta": meta},
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
            }
        )


class VerifyFlightPaymentView(APIView):
    """Endpoint for verifying flight booking payments. This view checks the payment status with Flutterwave using the transaction reference (tx_ref), updates the payment record accordingly, and if successful, creates the flight order with Amadeus. It also handles various error scenarios such as payment verification failure, amount mismatch, and currency mismatch.
    Expected request data:
    {
        "tx_ref": "unique_transaction_reference",
        "flight_offer": { ... },  // Optional, can also be retrieved from payment meta
        "travelers": [ ... ]  // Optional, can also be retrieved from payment meta
        // other optional fields for flight details...
    }
    Expected response data on success:
    {
        "message": "Flight booked successfully",
        "booking_id": 1
    }
    Expected response data on failure:
    {
        "error": "Payment verification failed",
        "details": { ... }  // Details from Flutterwave verification response
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    @swagger_auto_schema(operation_description="Verify payment and finalize flight booking.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["tx_ref"],
            properties={
                "tx_ref": openapi.Schema(type=openapi.TYPE_STRING, description="Transaction reference"),
                "flight_offer": openapi.Schema(type=openapi.TYPE_OBJECT, description="Optional flight offer"),
                "travelers": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
                "departure_city": openapi.Schema(type=openapi.TYPE_STRING),
                "arrival_city": openapi.Schema(type=openapi.TYPE_STRING),
                "departure_date": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                "return_date": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                "airline": openapi.Schema(type=openapi.TYPE_STRING),
                "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            200: openapi.Response(
                description="Flight booked successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "booking_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
            ),
            400: "Payment verification failed or invalid data",
            404: "Payment not found",
        },
    )
    def post(self, request):
        """Verifies the payment for a flight booking using the transaction reference (tx_ref). This endpoint checks the payment status with Flutterwave, updates the payment record, and if successful, creates the flight order with Amadeus. It also handles various error scenarios such as payment verification failure, amount mismatch, and currency mismatch.
        Expected request data:
        {
            "tx_ref": "unique_transaction_reference",
            "flight_offer": { ... },  // Optional, can also be retrieved from payment meta
            "travelers": [ ... ]  // Optional, can also be retrieved from payment meta
            // other optional fields for flight details...
        }
        Expected response data on success:
        {
            "message": "Flight booked successfully",
            "booking_id": 1
        }
        Expected response data on failure:
        {
            "error": "Payment verification failed",
            "details": { ... }  // Details from Flutterwave verification response
        }
        """

        tx_ref = request.data.get("tx_ref")
        if not tx_ref:
            return Response({"error": "tx_ref is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.select_for_update().get(
                tx_ref=tx_ref,
                booking__user=request.user,
            )
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        if payment.status == "succeeded":
            return Response(
                {"message": "Already verified", "booking_id": payment.booking.id},
                status=status.HTTP_200_OK,
            )

        verification = FlutterwaveService().verify_payment(tx_ref)
        meta = (payment.raw_response or {}).get("meta", {})

        def mark_verification_failed(message, details, status_code=status.HTTP_400_BAD_REQUEST):
            payment.status = "failed"
            payment.raw_response = {
                "meta": meta,
                "verification": details,
            }
            payment.save()
            BookingEngine.update_status(payment.booking, "failed")
            transaction_obj = get_or_create_transaction(
                booking=payment.booking,
                reference=payment.tx_ref,
                amount=payment.amount,
                currency=payment.currency,
            )
            mark_transaction_failed(transaction_obj, provider_response=payment.raw_response)
            return Response({"error": message, "details": details}, status=status_code)

        def mark_booking_failed(message, details=None, status_code=status.HTTP_400_BAD_REQUEST):
            payment.status = "booking_failed"
            payment.raw_response = {
                "meta": meta,
                "verification": verification,
                "booking_error": details,
            }
            payment.save()
            BookingEngine.update_status(payment.booking, "failed")
            transaction_obj = get_or_create_transaction(
                booking=payment.booking,
                reference=payment.tx_ref,
                amount=payment.amount,
                currency=payment.currency,
            )
            mark_transaction_failed(transaction_obj, provider_response=payment.raw_response)
            log_action(
                actor=payment.booking.user,
                action="booking_failed",
                metadata={"booking_id": str(payment.booking.id), "service_type": "flight"},
            )
            payload = {"error": message}
            if details is not None:
                payload["details"] = details
            return Response(payload, status=status_code)

        def finalize_successful_payment(updated_meta):
            payment.status = "succeeded"
            payment.flutterwave_charge_id = str(verification_data.get("id"))
            payment.paid_at = timezone.now()
            payment.raw_response = {
                "meta": updated_meta,
                "verification": verification,
            }
            payment.save()
            BookingEngine.attach_payment(
                payment.booking,
                "confirmed",
                payment_reference=str(verification_data.get("id")),
            )
            transaction_obj = get_or_create_transaction(
                booking=payment.booking,
                reference=payment.tx_ref,
                amount=payment.amount,
                currency=payment.currency,
            )
            mark_transaction_success(transaction_obj, provider_response=payment.raw_response)
            create_notification(
                user=payment.booking.user,
                title="Booking confirmed",
                message="Your flight booking is confirmed.",
                notification_type="success",
            )
            log_action(
                actor=payment.booking.user,
                action="booking_confirmed",
                metadata={"booking_id": str(payment.booking.id), "service_type": "flight"},
            )

        if verification.get("status") != "success":
            return mark_verification_failed("Payment verification failed", verification)

        verification_data = verification.get("data", {})
        if verification_data.get("status") != "successful":
            return mark_verification_failed("Payment not successful", verification)

        try:
            verified_amount = Decimal(str(verification_data.get("amount")))
        except (InvalidOperation, TypeError, ValueError):
            verified_amount = None

        if verified_amount is None or verified_amount != payment.amount:
            return mark_verification_failed("Payment amount mismatch", verification)

        if verification_data.get("currency") != payment.currency:
            return mark_verification_failed("Payment currency mismatch", verification)

        if FlightBooking.objects.filter(booking=payment.booking).exists():
            finalize_successful_payment(meta)
            return Response(
                {"message": "Flight booked successfully", "booking_id": payment.booking.id},
                status=status.HTTP_200_OK,
            )

        flight_offer = request.data.get("flight_offer") or meta.get("flight_offer")
        travelers = request.data.get("travelers") or meta.get("travelers")
        if not flight_offer or not travelers:
            return mark_booking_failed(
                "flight_offer and travelers are required to create the flight order"
            )

        try:
            flight_order = AmadeusService.create_flight_order(
                flight_offer,
                travelers,
            )
        except Exception as exc:
            return mark_booking_failed(
                "Airline booking failed",
                details=str(exc),
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if flight_order.get("id"):
            payment.booking.external_service_id = flight_order["id"]
            payment.booking.save()

        def get_detail(field_name, default=None):
            value = request.data.get(field_name)
            if value not in (None, ""):
                return value
            return meta.get(field_name, default)

        departure_city = get_detail("departure_city")
        arrival_city = get_detail("arrival_city")
        departure_date = get_detail("departure_date")
        airline = get_detail("airline")
        passengers = get_detail("passengers", 1)
        return_date = get_detail("return_date")

        if not departure_city or not arrival_city or not departure_date or not airline:
            return mark_booking_failed(
                "departure_city, arrival_city, departure_date, and airline are required"
            )

        FlightBooking.objects.create(
            booking=payment.booking,
            departure_city=departure_city,
            arrival_city=arrival_city,
            departure_date=departure_date,
            return_date=return_date,
            airline=airline,
            passengers=int(passengers) if passengers is not None else 1,
        )

        updated_meta = {
            **meta,
            "flight_offer": flight_offer,
            "travelers": travelers,
            "departure_city": departure_city,
            "arrival_city": arrival_city,
            "departure_date": departure_date,
            "return_date": return_date,
            "airline": airline,
            "passengers": passengers,
        }

        finalize_successful_payment(updated_meta)

        return Response(
            {"message": "Flight booked successfully", "booking_id": payment.booking.id},
            status=status.HTTP_201_CREATED,
        )
