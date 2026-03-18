import hmac

from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status
from .models import Payment
from .serializers import PaymentSerializer
from app.services.flutterwave import FlutterwaveService
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.conf import settings
from django.http import HttpResponse
from app.services.booking_engine import BookingEngine
from app.services.reference_generator import generate_booking_reference
from app.payments.tasks import process_successful_payment
from app.payments.services import PaymentVerificationService
from app.transactions.services import get_or_create_transaction, mark_transaction_failed
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


def _signature_to_bytes(value):
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode()
    return None


# --- ViewSet for Admin/User Payment access ---
@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List payments.",
                                  manual_parameters=[
                                     openapi.Parameter(
                                         'booking_id', openapi.IN_QUERY, description="Filter payments by booking ID", type=openapi.TYPE_INTEGER
                                     ),
                                     openapi.Parameter(
                                         'status', openapi.IN_QUERY, description="Filter payments by status (pending, succeeded, failed)", type=openapi.TYPE_STRING
                                     ),
                                 ]
    )
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a payment by ID.",
                                  responses={
                                     200: PaymentSerializer(),
                                     404: "Payment not found"
                                 }
    )
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(operation_description="Create a payment record.",
                                  request_body=PaymentSerializer,
                                  responses={
                                     201: PaymentSerializer(),
                                     400: "Invalid input data"
                                 }
    )
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(operation_description="Update a payment.",
                                  request_body=PaymentSerializer,
                                  responses={
                                     200: PaymentSerializer(),
                                     400: "Invalid input data",
                                     404: "Payment not found"
                                 }
    )
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(operation_description="Partially update a payment.",
                                  request_body=PaymentSerializer,
                                  responses={
                                     200: PaymentSerializer(),
                                     400: "Invalid input data",
                                     404: "Payment not found"
                                 }
    )
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Delete a payment.",
                                  responses={
                                     204: "Payment deleted successfully",
                                     404: "Payment not found"
                                 }
    )
)
class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing payments. Regular users can only see and manage their own payments, while admin users can see and manage all payments.
    Expected URL for listing payments: /payments/
    Expected URL for retrieving a payment: /payments/<payment_id>/
    Expected URL for creating a payment: /payments/create/
    Expected URL for updating a payment: /payments/<payment_id>/
    Expected URL for deleting a payment: /payments/<payment_id>/
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Admin users can see all payments, regular users can only see their own payments."""
        if getattr(self, 'swagger_fake_view', False):
            return Payment.objects.none()

        user = self.request.user
    
        if getattr(user, "user_type", None) == "admin":
            return Payment.objects.all()
        return Payment.objects.filter(booking__user=user)


# --- Flutterwave Webhook ---
#/payments/webhook/ - handle Flutterwave payment webhooks
class FlutterwaveWebhookView(APIView):
    """Endpoint to handle Flutterwave payment webhooks. This endpoint receives payment status updates from Flutterwave and processes them accordingly. It verifies the signature of the incoming request to ensure it is from Flutterwave, then checks the payment status and updates the corresponding payment record in the database. If the payment is successful, it attaches the payment to the booking and triggers any necessary post-payment processing. If the payment fails, it marks the payment as failed and updates the booking status.
    Expected request headers:
    - verif-hash: The secret hash configured in Flutterwave for webhook verification (required)
    Expected request body:
    {
        "id": 123456",
        "txRef": "unique_transaction_reference",
        "amount": 100.00,
        "currency": "USD",
        "status": "successful"
        // other fields returned by Flutterwave...
    }
    """
    authentication_classes = []
    permission_classes = []

    @transaction.atomic
    @swagger_auto_schema(operation_description="Handle Flutterwave webhook callbacks.",
                             request_body=openapi.Schema(
                                 type=openapi.TYPE_OBJECT,
                                 properties={
                                              "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                              "txRef": openapi.Schema(type=openapi.TYPE_STRING),
                                              "amount": openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
                                              "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                              "status": openapi.Schema(type=openapi.TYPE_STRING)
                                 }
                             )
    )
    def post(self, request):
        """Endpoint to handle Flutterwave payment webhooks. This endpoint receives payment status updates from Flutterwave and processes them accordingly. It verifies the signature of the incoming request to ensure it is from Flutterwave, then checks the payment status and updates the corresponding payment record in the database. If the payment is successful, it attaches the payment to the booking and triggers any necessary post-payment processing. If the payment fails, it marks the payment as failed and updates the booking status.
        Expected request headers:
        - verif-hash: The secret hash configured in Flutterwave for webhook verification (required)
        Expected request body:
        {
            "id": 123456",
            "txRef": "unique_transaction_reference",
            "amount": 100.00,
            "currency": "USD",
            "status": "successful"
            // other fields returned by Flutterwave...
        }
        Expected response on successful processing:
        {
            "message": "Payment processed"
        }
        Expected response on failed processing:
        {
            "error": "Invalid signature" // if signature verification fails
        }
        {
            "error": "Payment not found" // if no matching payment record is found
        }
        {
            "status": "failed" // if payment status is failed
        }
        """

        signature = request.headers.get("verif-hash")
        expected_signature = settings.FLUTTERWAVE_SECRET_HASH
        if not expected_signature:
            return Response(
                {"error": "Payment verification unavailable due to configuration error"},
                status=503,
            )
        signature_bytes = _signature_to_bytes(signature)
        expected_signature_bytes = _signature_to_bytes(expected_signature)
        if not signature_bytes:
            return Response({"error": "Missing signature"}, status=400)
        if not expected_signature_bytes:
            return Response(
                {"error": "Payment verification unavailable due to configuration error"},
                status=503,
            )
        if not hmac.compare_digest(signature_bytes, expected_signature_bytes):
            return Response({"error": "Invalid signature"}, status=400)

        data = request.data
        tx_ref = data.get("tx_ref") or data.get("txRef")
        if not tx_ref and isinstance(data.get("data"), dict):
            tx_ref = data["data"].get("tx_ref") or data["data"].get("txRef")
        if not tx_ref:
            return Response({"error": "txRef missing"}, status=400)

        try:
            payment = Payment.objects.select_for_update().get(tx_ref=tx_ref)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

        # Idempotent protection
        if payment.status == "succeeded":
            return Response({"message": "Already processed"}, status=200)

        verification_result = PaymentVerificationService.apply_verification(
            payment,
            verification_response=data,
            source="webhook",
            mark_failed_on_gateway_error=True,
        )
        if verification_result.is_successful:
            BookingEngine.attach_payment(payment.booking, 'confirmed')

            transaction.on_commit(
                lambda: process_successful_payment.delay(str(payment.id))
            )

            return Response({"message": "Payment processed"}, status=200)

        BookingEngine.update_status(payment.booking, 'failed')

        transaction_obj = get_or_create_transaction(
            booking=payment.booking,
            reference=payment.tx_ref,
            amount=payment.amount,
            currency=payment.currency,
        )
        mark_transaction_failed(transaction_obj, provider_response=payment.raw_response)

        return Response({"status": "failed"}, status=200)

#/payments/initiate-card/ - initialize a card payment for a booking
class CardPaymentInitView(APIView):
    """Endpoint for initializing a card payment for a booking. This endpoint creates a pending payment record and returns the Flutterwave payment link that the user can use to complete the card payment. The user must provide the booking ID, amount, currency, and a unique transaction reference (tx_ref). An idempotency key is required in the headers to prevent duplicate payments. The response includes the payment details and the Flutterwave payment link.
    Expected request data:
    {
        "booking_id": 1,
        "amount": 100.00,
        "currency": "NGN",
        "tx_ref": "unique_transaction_reference"
    }
    Expected response data:
    {
    "payment": {
        "id": 1,
        "booking": 1,
        "amount": 100.00,
        "currency": "NGN",
        "payment_method": "card",
        "tx_ref": "unique_transaction_reference",
        "status": "pending",
        "paid_at": null,
        "created_at": "2023-10-01T12:00:00Z"
    },
    "gateway": {
        "link": "https://flutterwave.com/pay/unique_transaction_reference",
        "flw_ref": "FLW123456",
        "tx_ref": "unique_transaction_reference"
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    @swagger_auto_schema(operation_description="Initiate a card payment for a booking.",
                             request_body=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                                "booking_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                "amount": openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
                                                "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                "tx_ref": openapi.Schema(type=openapi.TYPE_STRING),
                                            }
                                ),
                             )
    def post(self, request):
        """Endpoint for initializing a card payment for a booking. This endpoint creates a pending payment record and returns the Flutterwave payment link that the user can use to complete the card payment. The user must provide the booking ID, amount, currency, and a unique transaction reference (tx_ref). An idempotency key is required in the headers to prevent duplicate payments. The response includes the payment details and the Flutterwave payment link.
        Expected request data:
        {
            "booking_id": 1,
            "amount": 100.00,
            "currency": "NGN",
            "tx_ref": "unique_transaction_reference"
        }
        """

        booking_id = request.data.get("booking_id")
        amount = request.data.get("amount")
        currency = request.data.get("currency", "NGN")
        tx_ref = request.data.get("tx_ref")
        idempotency_key = request.headers.get("Idempotency-Key")
        trace_id = request.headers.get("X-Trace-Id")

        if not idempotency_key:
            return Response(
                {"error": "Idempotency-Key header required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not tx_ref:
            tx_ref = generate_booking_reference("pay")

        # Prevent duplicate request
        existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return Response(PaymentSerializer(existing).data)

        from app.bookings.models import Booking
        try:
            booking = Booking.objects.select_for_update().get(
                id=booking_id, user=request.user
            )
        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if amount is None:
            amount = booking.total_price
        if amount is None:
            return Response(
                {"error": "amount is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer_email = request.user.email

        flutterwave_response = FlutterwaveService().initiate_card_payment(
            amount, currency, customer_email, tx_ref
        )

        payment = Payment.objects.create(
            booking=booking,
            amount=amount,
            currency=currency,
            payment_method="card",
            tx_ref=tx_ref,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
            status="pending",
        )

        get_or_create_transaction(
            booking=booking,
            reference=tx_ref,
            amount=amount,
            currency=currency,
        )

        return Response({
            "payment": PaymentSerializer(payment).data,
            "gateway": flutterwave_response,
        })
#/payments/initiate-bank-transfer/ - initialize a bank transfer payment for a booking
class BankTransferInitView(APIView):
    """Endpoint for initializing a bank transfer payment for a booking. This endpoint creates a pending payment record and returns the bank details that the user should use to complete the transfer. The user must provide the booking ID, amount, and optionally the currency (default is NGN). An idempotency key is required in the headers to prevent duplicate payments. The response includes the payment details and the bank information needed for the transfer.
    Expected request data:
    {
        "booking_id": 1,
        "amount": 100.00,
        "currency": "USD" // optional, defaults to NGN
    }
    Expected response data:
    {
    "payment": {
        "id": 1,
        "booking": 1,
        "amount": 100.00,
        "currency": "USD",
        "payment_method": "bank_transfer",
        "tx_ref": "unique_transaction_reference",
        "status": "pending",
        "paid_at": null,
        "created_at": "2023-10-01T12:00:00Z"
    },
    "bank_details": {
        "account_name": "Static Account Name",
        "account_number": "1234567890",
        "bank_name": "Static Bank Name",
        "reference": "unique_transaction_reference"
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    @swagger_auto_schema(operation_description="Initiate a bank transfer payment for a booking.",
                             request_body=openapi.Schema(
                                 type=openapi.TYPE_OBJECT,
                                 properties={
                                     "booking_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                     "amount": openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
                                     "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                 }
                             ),
    )
    def post(self, request):
        """Initializes a bank transfer payment for a booking. This endpoint creates a pending payment record and returns the bank details that the user should use to complete the transfer. The user must provide the booking ID, amount, and optionally the currency (default is NGN). An idempotency key is required in the headers to prevent duplicate payments. The response includes the payment details and the bank information needed for the transfer.
        Expected request data:
        {
            "booking_id": 1,
            "amount": 100.00,
            "currency": "USD" // optional, defaults to NGN
        }
        Expected response data:
        {
            "payment": {
                "id": 1,
                "booking": 1,
                "amount": 100.00,
                "currency": "USD",
                "payment_method": "bank_transfer",
                "tx_ref": "unique_transaction_reference",
                "status": "pending",
                "paid_at": null,
                "created_at": "2023-10-01T12:00:00Z"
            },
            "bank_details": {
                "account_name": "Static Account Name",
                "account_number": "1234567890",
                "bank_name": "Static Bank Name",
                "reference": "unique_transaction_reference"
            }
        }
        """

        booking_id = request.data.get("booking_id")
        amount = request.data.get("amount")
        currency = request.data.get("currency", "NGN")

        idempotency_key = request.headers.get("Idempotency-Key")
        trace_id = request.headers.get("X-Trace-Id")

        if not idempotency_key:
            return Response(
                {"error": "Idempotency-Key required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return Response(PaymentSerializer(existing).data)

        from app.bookings.models import Booking
        try:
            booking = Booking.objects.select_for_update().get(
                id=booking_id, user=request.user
            )
        except Booking.DoesNotExist:
            return Response(
                {"error": "Booking not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        import uuid
        tx_ref = str(uuid.uuid4())

        if amount is None:
            amount = booking.total_price
        if amount is None:
            return Response(
                {"error": "amount is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment = Payment.objects.create(
            booking=booking,
            amount=amount,
            currency=currency,
            payment_method="bank_transfer",
            tx_ref=tx_ref,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
            status="pending",
        )

        get_or_create_transaction(
            booking=booking,
            reference=tx_ref,
            amount=amount,
            currency=currency,
        )

        return Response({
            "payment": PaymentSerializer(payment).data,
            "bank_details": {
                "account_name": settings.STATIC_ACCOUNT_NAME,
                "account_number": settings.STATIC_ACCOUNT_NUMBER,
                "bank_name": settings.STATIC_BANK_NAME,
                "reference": tx_ref,
            }
        })

#/payments/verify/ - verify a payment by tx_ref using Flutterwave API
class PaymentVerificationView(APIView):
    """Endpoint for verifying a payment by its transaction reference (tx_ref) using the Flutterwave API. This endpoint checks the payment status and details returned by Flutterwave to ensure that the payment was successful and matches the expected amount and currency. If the payment is verified successfully, it updates the payment record and attaches it to the booking. If verification fails, it marks the payment as failed and updates the booking status accordingly.
    Expected request data:
    {
        "tx_ref": "unique_transaction_reference"
    }
    Expected response data on successful verification:
    {
        "message": "Payment verified successfully",
        "payment": {
            "id": 1,
            "booking": 1,
            "amount": 100.00,
            "currency": "USD",
            "payment_method": "card",
            "tx_ref": "unique_transaction_reference",
            "status": "succeeded",
            "paid_at": "2023-10-01T12:00:00Z",
            "created_at": "2023-10-01T11:00:00Z"
        }
    }
    Expected response data on failed verification:
    {
        "error": "Payment verification failed",
        "gateway_response": {
            "status": "failed",
            "data": {
                "id": 123456,
                "txRef": "unique_transaction_reference",
                "amount": 100.00,
                "currency": "USD",
                "status": "failed"
                // other fields returned by Flutterwave...
            }
        }
    }
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    @swagger_auto_schema(operation_description="Verify a payment by tx_ref.",
                             request_body=openapi.Schema(
                                 type=openapi.TYPE_OBJECT,
                                 properties={
                                     "tx_ref": openapi.Schema(type=openapi.TYPE_STRING)
                                 }
                             ),
                             responses={
                                 200: openapi.Schema(
                                     type=openapi.TYPE_OBJECT,
                                     properties={
                                         "message": openapi.Schema(type=openapi.TYPE_STRING),
                                         "payment": openapi.Schema(
                                             type=openapi.TYPE_OBJECT,
                                             properties={
                                                 "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                 "booking": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                 "amount": openapi.Schema(type=openapi.TYPE_NUMBER, format='float'),
                                                 "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                 "payment_method": openapi.Schema(type=openapi.TYPE_STRING),
                                                 "tx_ref": openapi.Schema(type=openapi.TYPE_STRING),
                                                 "status": openapi.Schema(type=openapi.TYPE_STRING),
                                                 "paid_at": openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                                 "created_at": openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                             }
                                         )
                                     }
                                    ),
                             }
    )
    def post(self, request):
        """Verifies a payment by its transaction reference (tx_ref) using the Flutterwave API. This endpoint checks the payment status and details returned by Flutterwave to ensure that the payment was successful and matches the expected amount and currency. If the payment is verified successfully, it updates the payment record and attaches it to the booking. If verification fails, it marks the payment as failed and updates the booking status accordingly.
        Expected request data:
        {
            "tx_ref": "unique_transaction_reference"
        }
        """
        tx_ref = request.data.get("tx_ref")

        if not tx_ref:
            return Response({"error": "tx_ref required"}, status=400)

        try:
            payment = Payment.objects.select_for_update().get(
                tx_ref=tx_ref,
                booking__user=request.user
            )
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

        # If already processed → idempotent
        if payment.status == "succeeded":
            return Response({
                "message": "Already verified",
                "payment": PaymentSerializer(payment).data
            })

        # Call Flutterwave verify API
        verification_response = FlutterwaveService().verify_payment(tx_ref)
        verification_result = PaymentVerificationService.apply_verification(
            payment,
            verification_response=verification_response,
            source="api",
            mark_failed_on_gateway_error=False,
        )

        if verification_result.gateway_error:
            return Response(
                {
                    "error": "Verification failed",
                    "gateway_response": verification_response,
                },
                status=400,
            )

        if verification_result.is_successful:
            payment.refresh_from_db(fields=["status", "paid_at"])
            BookingEngine.attach_payment(payment.booking, "confirmed")

            transaction.on_commit(
                lambda: process_successful_payment.delay(str(payment.id))
            )

            return Response({
                "message": "Payment verified successfully",
                "payment": PaymentSerializer(payment).data
            })

        BookingEngine.update_status(payment.booking, "failed")

        transaction_obj = get_or_create_transaction(
            booking=payment.booking,
            reference=payment.tx_ref,
            amount=payment.amount,
            currency=payment.currency,
        )
        mark_transaction_failed(transaction_obj, provider_response=payment.raw_response)

        return Response({
            "error": "Payment verification failed",
            "gateway_response": verification_response
        }, status=400)
    


#/payments/redirect/ - handle payment redirects from Flutterwave
class PaymentRedirectView(APIView):
    """A simple view to handle redirects after payment attempts. It displays the transaction reference and status returned by Flutterwave. This view can be used to show a confirmation message to users after they complete a payment on the Flutterwave platform.
    Expected URL: /payments/redirect/
    Expected query parameters:
    - tx_ref: The transaction reference returned by Flutterwave (required)
    - status: The status of the payment attempt (required)
    Example URL: /payments/redirect/?tx_ref=unique_transaction_reference&status=successful
    Expected response: An HTML page displaying the payment status and reference.
    <h2>Payment Attempt Completed</h2>
    <p>Status: successful</p>
    <p>Reference: unique_transaction_reference</p>
    <p>You may now return to the app.</p>
    """
    authentication_classes = []
    permission_classes = []

    @swagger_auto_schema(operation_description="Payment redirect landing page.",
                             manual_parameters=[
                                 openapi.Parameter(
                                     'tx_ref', openapi.IN_QUERY, description="The transaction reference returned by Flutterwave", type=openapi.TYPE_STRING
                                 ),
                                 openapi.Parameter(
                                     'status', openapi.IN_QUERY, description="The status of the payment attempt", type=openapi.TYPE_STRING
                                 ),
                             ]
    )
    def get(self, request):
        """Simple view to handle redirects after payment attempts. It displays the transaction reference and status returned by Flutterwave. This view can be used to show a confirmation message to users after they complete a payment on the Flutterwave platform.
        Expected URL: /payments/redirect/
        Expected query parameters:
        - tx_ref: The transaction reference returned by Flutterwave (required)
        - status: The status of the payment attempt (required)
        Example URL: /payments/redirect/?tx_ref=unique_transaction_reference&status=successful
        Expected response: An HTML page displaying the payment status and reference.
        <h2>Payment Attempt Completed</h2>
        <p>Status: successful</p>
        <p>Reference: unique_transaction_reference</p>
        <p>You may now return to the app.</p>
        """
        tx_ref = request.GET.get("tx_ref")
        status_param = request.GET.get("status")

        return HttpResponse(
            f"""
            <h2>Payment Attempt Completed</h2>
            <p>Status: {status_param}</p>
            <p>Reference: {tx_ref}</p>
            <p>You may now return to the app.</p>
            """
        )
