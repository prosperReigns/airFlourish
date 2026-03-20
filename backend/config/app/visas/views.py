import logging
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction, models
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from app.core.pagination import DefaultPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from app.notifications.services import create_notification
from app.payments.models import Payment
from app.payments.services import PaymentVerificationService
from app.payments.tasks import process_successful_payment
from app.services.booking_engine import BookingEngine
from app.services.flutterwave import FlutterwaveService
from app.services.reference_generator import generate_booking_reference
from app.transactions.services import (
    get_or_create_transaction,
    mark_transaction_failed,
)
from app.users.permissions import IsAdminUserType
from app.visas.models import VisaApplication, VisaPayment, VisaType
from app.visas.serializers import (
    VisaApplicationSerializer,
    VisaDocumentSerializer,
    VisaPaymentSerializer,
    VisaTypeSerializer,
)
from app.visas.services.validation_service import validate_application

logger = logging.getLogger(__name__)


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


class VisaApplicationViewSet(viewsets.ModelViewSet):
    queryset = VisaApplication.objects.all()
    serializer_class = VisaApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return VisaApplication.objects.none()
        user = self.request.user
        base_queryset = VisaApplication.objects.select_related(
            "user", "agent", "visa_type", "booking"
        ).prefetch_related("documents")
        if getattr(user, "user_type", None) == "admin":
            return base_queryset
        if getattr(user, "user_type", None) == "agent":
            return base_queryset.filter(models.Q(user=user) | models.Q(agent=user))
        return base_queryset.filter(user=user)

    def _is_admin(self, user):
        return getattr(user, "user_type", None) == "admin"

    def _is_agent(self, user):
        return getattr(user, "user_type", None) == "agent"

    def _resolve_target_user(self, payload):
        user_value = payload.get("user")
        if user_value in (None, ""):
            return None
        try:
            return get_user_model().objects.get(id=user_value)
        except (TypeError, ValueError, get_user_model().DoesNotExist):
            raise ValidationError("Specified user does not exist")

    def _ensure_internal_fields_allowed(self, request, allow_user_assignment=False):
        forbidden_fields = {"internal_notes", "embassy_review_status", "user", "agent"}
        if allow_user_assignment:
            forbidden_fields = forbidden_fields.difference({"user"})
        if not self._is_admin(request.user):
            restricted = forbidden_fields.intersection(request.data.keys())
            if restricted:
                return Response(
                    {"error": "You do not have permission to modify internal fields."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        return None

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = self._ensure_internal_fields_allowed(
            request, allow_user_assignment=self._is_agent(request.user)
        )
        if response:
            return response

        user = request.user
        target_user = user
        agent = None

        if self._is_agent(user):
            agent = user
            try:
                target_user = self._resolve_target_user(request.data) or user
            except ValidationError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        elif self._is_admin(user):
            try:
                resolved_user = self._resolve_target_user(request.data)
            except ValidationError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            if resolved_user:
                target_user = resolved_user
        else:
            if "user" in request.data or "agent" in request.data:
                return Response(
                    {"error": "User assignment is not allowed"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer.save(user=target_user, agent=agent, status=VisaApplication.STATUS_DRAFT)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def _ensure_editable(self, application):
        if application.is_locked:
            return False, "Application is locked and cannot be edited"
        if application.status in {
            VisaApplication.STATUS_SUBMITTED,
            VisaApplication.STATUS_UNDER_EMBASSY_REVIEW,
            VisaApplication.STATUS_UNDER_REVIEW,
            VisaApplication.STATUS_APPROVED,
            VisaApplication.STATUS_REJECTED,
        }:
            return False, f"Cannot edit application in status {application.status}"
        if application.status in {
            VisaApplication.STATUS_READY_FOR_SUBMISSION,
            VisaApplication.STATUS_READY_FOR_PAYMENT,
            VisaApplication.STATUS_PAID,
        }:
            return False, "Cannot edit after validation"
        return True, None

    def _is_internal_only_update(self, request):
        internal_fields = {"internal_notes", "embassy_review_status"}
        if not request.data:
            return False
        return set(request.data.keys()).issubset(internal_fields)

    def _has_successful_payment(self, application):
        if application.booking_id:
            if Payment.objects.filter(
                booking_id=application.booking_id, status="succeeded"
            ).exists():
                return True
        return application.payments.filter(status=VisaPayment.STATUS_SUCCESSFUL).exists()

    def update(self, request, *args, **kwargs):
        application = self.get_object()
        if not (self._is_admin(request.user) and self._is_internal_only_update(request)):
            ok, error = self._ensure_editable(application)
            if not ok:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        response = self._ensure_internal_fields_allowed(request)
        if response:
            return response
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        application = self.get_object()
        if not (self._is_admin(request.user) and self._is_internal_only_update(request)):
            ok, error = self._ensure_editable(application)
            if not ok:
                return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        response = self._ensure_internal_fields_allowed(request)
        if response:
            return response
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="documents")
    @swagger_auto_schema(
        operation_description="Upload a document for a visa application.",
        request_body=VisaDocumentSerializer,
        responses={201: VisaDocumentSerializer()},
    )
    def upload_documents(self, request, pk=None):
        application = self.get_object()
        ok, error = self._ensure_editable(application)
        if not ok:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        serializer = VisaDocumentSerializer(
            data=request.data, context={"application": application}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(application=application)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="validate")
    @swagger_auto_schema(operation_description="Validate visa application completeness.")
    def validate_application(self, request, pk=None):
        application = self.get_object()
        ok, error = self._ensure_editable(application)
        if not ok:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        if application.status not in {VisaApplication.STATUS_DRAFT, VisaApplication.STATUS_INCOMPLETE}:
            return Response(
                {"error": "Validation is only allowed in draft or incomplete status"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_valid, errors = validate_application(application)
        if is_valid:
            try:
                application.transition_to(VisaApplication.STATUS_READY_FOR_SUBMISSION)
            except ValidationError as exc:
                return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"status": application.status}, status=status.HTTP_200_OK)

        application.status = VisaApplication.STATUS_INCOMPLETE
        application.save(update_fields=["status", "updated_at"])
        return Response(
            {"status": application.status, "errors": errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _initiate_payment(self, request, application, allowed_statuses=None):
        if application.is_locked:
            return Response(
                {"error": "Application is locked and cannot be paid"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not application.user or not application.user.email:
            return Response(
                {"error": "Application user is required for payment"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if allowed_statuses is None:
            allowed_statuses = {VisaApplication.STATUS_READY_FOR_SUBMISSION}
        if application.status not in allowed_statuses:
            return Response(
                {"error": "Application is not ready for payment"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            return Response(
                {"error": "Idempotency-Key header required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = _to_decimal(request.data.get("amount"))
        currency = request.data.get("currency")
        if amount is None or not currency:
            return Response(
                {"error": "amount and currency are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment_method = (request.data.get("payment_method") or "").lower().strip()
        if payment_method and payment_method not in {"card", "bank_transfer"}:
            return Response(
                {"error": "payment_method must be 'card' or 'bank_transfer'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_payment = Payment.objects.filter(idempotency_key=idempotency_key).first()
        if existing_payment:
            raw_response = existing_payment.raw_response or {}
            meta = raw_response.get("meta") if isinstance(raw_response, dict) else {}
            if isinstance(meta, dict):
                existing_app_id = meta.get("application_id")
                if existing_app_id and existing_app_id != application.id:
                    return Response(
                        {"error": "Idempotency-Key reuse with different application"},
                        status=status.HTTP_409_CONFLICT,
                    )
            return Response(
                {
                    "payment_link": raw_response.get("payment_link"),
                    "tx_ref": existing_payment.tx_ref,
                    "booking_id": existing_payment.booking_id,
                    "payment_options": raw_response.get("payment_options"),
                    "bank_transfer_available": raw_response.get("bank_transfer_available"),
                },
                status=status.HTTP_200_OK,
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
            amount=amount,
            currency=currency,
            customer_email=application.user.email,
            tx_ref=tx_ref,
            payment_options=payment_options,
        )
        if payment_response.get("status") == "error":
            return Response(
                {"error": "Payment initiation failed", "details": payment_response.get("message")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking = application.booking
        if booking:
            if booking.user_id != application.user_id:
                return Response(
                    {"error": "Booking does not belong to this user"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if booking.service_type != "visa":
                return Response(
                    {"error": "Existing booking is not a visa booking"},
                    status=status.HTTP_409_CONFLICT,
                )
            if booking.total_price and booking.total_price != amount:
                return Response(
                    {"error": "amount does not match existing booking"},
                    status=status.HTTP_409_CONFLICT,
                )
            if booking.currency and booking.currency != currency:
                return Response(
                    {"error": "currency does not match existing booking"},
                    status=status.HTTP_409_CONFLICT,
                )
            if booking.total_price is None or booking.currency != currency:
                booking.total_price = amount
                booking.currency = currency
                booking.save(update_fields=["total_price", "currency"])
        else:
            booking = BookingEngine.create_booking(
                user=application.user,
                service_type="visa",
                total_price=amount,
                currency=currency,
            )
            application.booking = booking
            application.save(update_fields=["booking", "updated_at"])

        meta = {
            "application_id": application.id,
            "visa_type": application.visa_type.code if application.visa_type else None,
            "amount": str(amount),
            "currency": currency,
        }

        Payment.objects.create(
            booking=booking,
            tx_ref=tx_ref,
            amount=amount,
            currency=currency,
            payment_method=payment_method or "card",
            status="pending",
            idempotency_key=idempotency_key,
            trace_id=request.headers.get("X-Trace-Id"),
            raw_response={
                "meta": meta,
                "payment_link": payment_response.get("data", {}).get("link"),
                "payment_options": payment_options,
                "bank_transfer_available": bank_transfer_available,
            },
        )

        get_or_create_transaction(
            booking=booking,
            reference=tx_ref,
            amount=amount,
            currency=currency,
        )

        payload = {
            "payment_link": payment_response.get("data", {}).get("link"),
            "tx_ref": tx_ref,
            "booking_id": booking.id,
            "payment_options": payment_options,
            "bank_transfer_available": bank_transfer_available,
        }
        return Response(
            payload,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="checkout")
    @swagger_auto_schema(
        operation_description="Initiate visa payment (idempotent).",
        manual_parameters=[
            openapi.Parameter(
                "Idempotency-Key",
                openapi.IN_HEADER,
                description="Required for checkout",
                type=openapi.TYPE_STRING,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["amount", "currency"],
            properties={
                "amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                "currency": openapi.Schema(type=openapi.TYPE_STRING),
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
                    "payment_options": openapi.Schema(type=openapi.TYPE_STRING),
                    "bank_transfer_available": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                },
            )
        },
    )
    def checkout(self, request, pk=None):
        application = self.get_object()
        return self._initiate_payment(
            request,
            application,
            allowed_statuses={
                VisaApplication.STATUS_READY_FOR_SUBMISSION,
                VisaApplication.STATUS_READY_FOR_PAYMENT,
            },
        )

    @action(detail=True, methods=["post"], url_path="pay")
    @swagger_auto_schema(
        operation_description="Pay for a visa application.",
        manual_parameters=[
            openapi.Parameter(
                "Idempotency-Key",
                openapi.IN_HEADER,
                description="Required for payment",
                type=openapi.TYPE_STRING,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["amount", "currency"],
            properties={
                "amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                "currency": openapi.Schema(type=openapi.TYPE_STRING),
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
                    "payment_options": openapi.Schema(type=openapi.TYPE_STRING),
                    "bank_transfer_available": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                },
            )
        },
    )
    def pay(self, request, pk=None):
        application = self.get_object()
        return self._initiate_payment(request, application)

    @action(detail=True, methods=["post"], url_path="submit")
    @swagger_auto_schema(operation_description="Submit a paid application.")
    def submit(self, request, pk=None):
        application = self.get_object()
        if application.is_locked:
            return Response(
                {"error": "Application is locked"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if application.status not in {
            VisaApplication.STATUS_READY_FOR_SUBMISSION,
            VisaApplication.STATUS_PAID,
        }:
            return Response(
                {"error": "Application must be ready for submission"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not self._has_successful_payment(application):
            return Response(
                {"error": "Payment is required before submission"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            application.transition_to(VisaApplication.STATUS_SUBMITTED)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        application.lock()

        create_notification(
            user=application.user,
            title="Visa application submitted",
            message="Your visa application has been submitted for review.",
            notification_type="success",
        )

        return Response({"status": application.status}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdminUserType])
    @swagger_auto_schema(operation_description="Move application to embassy review (admin).")
    def review(self, request, pk=None):
        application = self.get_object()
        if application.status != VisaApplication.STATUS_SUBMITTED:
            return Response(
                {"error": "Only submitted applications can be reviewed"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            application.transition_to(VisaApplication.STATUS_UNDER_EMBASSY_REVIEW)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        application.embassy_review_status = "in_review"
        application.save(update_fields=["embassy_review_status", "updated_at"])
        return Response({"status": application.status}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdminUserType])
    @swagger_auto_schema(operation_description="Approve application (admin).")
    def approve(self, request, pk=None):
        application = self.get_object()
        if application.status != VisaApplication.STATUS_UNDER_EMBASSY_REVIEW:
            return Response(
                {"error": "Application must be under embassy review"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            application.transition_to(VisaApplication.STATUS_APPROVED)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        create_notification(
            user=application.user,
            title="Visa approved",
            message="Your visa application has been approved.",
            notification_type="success",
        )

        return Response({"status": application.status}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAdminUserType])
    @swagger_auto_schema(operation_description="Reject application (admin).")
    def reject(self, request, pk=None):
        application = self.get_object()
        if application.status != VisaApplication.STATUS_UNDER_EMBASSY_REVIEW:
            return Response(
                {"error": "Application must be under embassy review"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            application.transition_to(VisaApplication.STATUS_REJECTED)
        except ValidationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        create_notification(
            user=application.user,
            title="Visa rejected",
            message="Your visa application was rejected.",
            notification_type="error",
        )

        return Response({"status": application.status}, status=status.HTTP_200_OK)


class VisaTypeView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description=(
            "List visa types by country. Endpoint: /api/visas/visa-types/ "
            "Supports ?country=NG&ordering=name&page=1&page_size=20"
        ),
        manual_parameters=[
            openapi.Parameter(
                "country",
                openapi.IN_QUERY,
                description="ISO country code (e.g., NG)",
                type=openapi.TYPE_STRING,
            )
            ,
            openapi.Parameter(
                "ordering",
                openapi.IN_QUERY,
                description="Order by: name, -name, code, -code, created_at, -created_at",
                type=openapi.TYPE_STRING,
            ),
            openapi.Parameter(
                "page",
                openapi.IN_QUERY,
                description="Page number",
                type=openapi.TYPE_INTEGER,
            ),
            openapi.Parameter(
                "page_size",
                openapi.IN_QUERY,
                description="Items per page (max 100)",
                type=openapi.TYPE_INTEGER,
            ),
        ],
        responses={
            200: openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    "country": openapi.Schema(type=openapi.TYPE_STRING),
                    "visa_types": openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                "code": openapi.Schema(type=openapi.TYPE_STRING),
                                "name": openapi.Schema(type=openapi.TYPE_STRING),
                                "country": openapi.Schema(type=openapi.TYPE_STRING),
                                "description": openapi.Schema(type=openapi.TYPE_STRING),
                                "price": openapi.Schema(type=openapi.TYPE_NUMBER),
                                "required_documents": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Items(type=openapi.TYPE_STRING),
                                ),
                                "processing_days": openapi.Schema(type=openapi.TYPE_INTEGER),
                                "is_active": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            },
                        ),
                    ),
                },
            ),
            400: "country is required",
        },
    )
    def get(self, request):
        country = (request.GET.get("country") or "").strip().upper()
        if not country:
            return Response({"error": "country is required"}, status=status.HTTP_400_BAD_REQUEST)

        ordering = (request.query_params.get("ordering") or "name").strip()
        allowed_ordering = {"name", "-name", "code", "-code", "created_at", "-created_at"}
        if ordering not in allowed_ordering:
            ordering = "name"

        queryset = VisaType.objects.filter(is_active=True, country__iexact=country).order_by(ordering)
        if not queryset.exists():
            queryset = VisaType.objects.filter(is_active=True, country="").order_by(ordering)

        paginator = DefaultPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = VisaTypeSerializer(page or queryset, many=True)

        if page is not None:
            return paginator.get_paginated_response(
                {"country": country, "visa_types": serializer.data}
            )

        return Response({"country": country, "visa_types": serializer.data}, status=status.HTTP_200_OK)


class VisaPaymentVerificationView(APIView):
    authentication_classes = []
    permission_classes = [IsAuthenticated, IsAdminUserType]

    @swagger_auto_schema(
        operation_description="Verify a visa payment (webhook or manual).",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "tx_ref": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
    )
    def post(self, request):
        payload = request.data or {}
        tx_ref = payload.get("tx_ref") or payload.get("txRef")
        if not tx_ref and isinstance(payload.get("data"), dict):
            tx_ref = payload["data"].get("tx_ref") or payload["data"].get("txRef")

        if not tx_ref:
            return Response({"error": "tx_ref is required"}, status=status.HTTP_400_BAD_REQUEST)

        payment = (
            Payment.objects.select_related("booking")
            .filter(tx_ref=tx_ref, booking__service_type="visa")
            .first()
        )
        if payment:
            if payment.status == "succeeded":
                return Response({"status": "already_verified"}, status=status.HTTP_200_OK)

            verification = payload
            source = "webhook"
            if "data" not in payload:
                verification = FlutterwaveService().verify_payment(tx_ref)
                source = "api"

            verification_result = PaymentVerificationService.apply_verification(
                payment,
                verification_response=verification,
                source=source,
                mark_failed_on_gateway_error=True,
            )
            if verification_result.is_successful:
                BookingEngine.attach_payment(payment.booking, "confirmed")
                transaction.on_commit(
                    lambda: process_successful_payment.delay(str(payment.id))
                )
                return Response({"status": "paid"}, status=status.HTTP_200_OK)

            BookingEngine.update_status(payment.booking, "failed")
            transaction_obj = get_or_create_transaction(
                booking=payment.booking,
                reference=payment.tx_ref,
                amount=payment.amount,
                currency=payment.currency,
            )
            mark_transaction_failed(transaction_obj, provider_response=payment.raw_response)
            return Response({"status": "failed"}, status=status.HTTP_400_BAD_REQUEST)

        legacy_payment = VisaPayment.objects.select_related("application").filter(tx_ref=tx_ref).first()
        if not legacy_payment:
            return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

        if legacy_payment.status == VisaPayment.STATUS_SUCCESSFUL:
            return Response(
                {"status": "already_verified", "payment": VisaPaymentSerializer(legacy_payment).data},
                status=status.HTTP_200_OK,
            )

        # If webhook payload doesn't include verification data, call Flutterwave.
        verification = payload
        if "data" not in payload:
            verification = FlutterwaveService().verify_payment(tx_ref)

        verification_data = verification.get("data") if isinstance(verification, dict) else None
        status_value = None
        reference = None
        if isinstance(verification_data, dict):
            status_value = verification_data.get("status")
            reference = verification_data.get("id")

        if status_value == "successful":
            legacy_payment.status = VisaPayment.STATUS_SUCCESSFUL
            if reference:
                legacy_payment.payment_reference = str(reference)
            legacy_payment.save(update_fields=["status", "payment_reference", "updated_at"])

            application = legacy_payment.application
            if application.status == VisaApplication.STATUS_READY_FOR_PAYMENT:
                try:
                    application.transition_to(VisaApplication.STATUS_PAID)
                except ValidationError:
                    logger.exception("Visa status transition failed for %s", application.id)

            create_notification(
                user=application.user,
                title="Visa payment successful",
                message="Your visa payment was received successfully.",
                notification_type="success",
            )

            return Response({"status": "paid"}, status=status.HTTP_200_OK)

        legacy_payment.status = VisaPayment.STATUS_FAILED
        legacy_payment.save(update_fields=["status", "updated_at"])
        return Response({"status": "failed"}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_description=(
            "List visa types (admin). Supports ?country=NG&is_active=true&search=tour"
            "&ordering=name&page=1&page_size=20"
        ),
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a visa type (admin)."),
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_description="Create a visa type (admin).",
        request_body=VisaTypeSerializer,
        responses={201: VisaTypeSerializer()},
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_description="Update a visa type (admin).",
        request_body=VisaTypeSerializer,
        responses={200: VisaTypeSerializer()},
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_description="Partially update a visa type (admin).",
        request_body=VisaTypeSerializer,
        responses={200: VisaTypeSerializer()},
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Delete a visa type (admin)."),
)
class VisaTypeAdminViewSet(viewsets.ModelViewSet):
    queryset = VisaType.objects.all()
    serializer_class = VisaTypeSerializer
    permission_classes = [IsAuthenticated, IsAdminUserType]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["name", "code", "country", "is_active", "created_at"]
    ordering = ["name"]
    pagination_class = DefaultPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        country = (self.request.query_params.get("country") or "").strip().upper()
        is_active = self.request.query_params.get("is_active")
        search = (self.request.query_params.get("search") or "").strip()

        if country:
            queryset = queryset.filter(country__iexact=country)
        if is_active is not None and is_active != "":
            is_active_value = str(is_active).lower() in {"1", "true", "yes"}
            queryset = queryset.filter(is_active=is_active_value)
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) | models.Q(code__icontains=search)
            )

        return queryset
