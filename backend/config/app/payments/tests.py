import uuid
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.payments.models import Payment
from app.payments.serializers import PaymentSerializer
from app.services.booking_engine import BookingEngine

PAYMENTS_URL = "/api/payments/payments/"
CARD_INIT_URL = "/api/payments/card/initiate/"
BANK_INIT_URL = "/api/payments/bank-transfer/initiate/"
VERIFY_URL = "/api/payments/verify/"
WEBHOOK_URL = "/api/payments/webhook/flutterwave/"
REDIRECT_URL = "/api/payments/redirect/"


def throttled_settings(rate):
    rates = dict(settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {}))
    rates.update({"anon": rate, "user": rate, "ip": rate})
    return {**settings.REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": rates}


class BasePaymentTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
            country="NG",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="password123",
            country="NG",
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="password123",
            country="NG",
            user_type="admin",
            is_staff=True,
        )

    def create_booking(self, user=None, service_type="hotel", total_price=Decimal("100.00")):
        return BookingEngine.create_booking(
            user=user or self.user,
            service_type=service_type,
            total_price=total_price,
            currency="NGN",
        )

    def create_payment(
        self,
        booking=None,
        amount=Decimal("100.00"),
        currency="NGN",
        payment_method="card",
        status="pending",
        tx_ref=None,
        idempotency_key=None,
        trace_id=None,
    ):
        booking = booking or self.create_booking()
        return Payment.objects.create(
            booking=booking,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            tx_ref=tx_ref or f"tx-{uuid.uuid4().hex}",
            status=status,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
        )


class PaymentModelTests(BasePaymentTestCase):
    def test_payment_str_and_defaults(self):
        booking = Booking.objects.create(
            user=self.user,
            service_type="hotel",
            reference_code="HOT-TEST-001",
            total_price=Decimal("120.00"),
            currency="NGN",
        )
        payment = Payment.objects.create(
            booking=booking,
            amount=Decimal("120.00"),
            currency="NGN",
            payment_method="card",
            tx_ref="tx-ref-001",
        )
        self.assertIn("pending", str(payment))
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.currency, "NGN")

    def test_payment_status_choices(self):
        payment = self.create_payment(status="succeeded")
        self.assertEqual(payment.status, "succeeded")

    def test_payment_method_choices(self):
        payment = self.create_payment(payment_method="bank_transfer")
        self.assertEqual(payment.payment_method, "bank_transfer")


class PaymentSerializerTests(BasePaymentTestCase):
    def setUp(self):
        super().setUp()
        self.booking = self.create_booking()
        self.payment = self.create_payment(booking=self.booking, tx_ref="tx-serializer-001")

    def test_payment_serializer_outputs_expected_fields(self):
        data = PaymentSerializer(self.payment).data
        self.assertEqual(data["booking"], self.booking.id)
        self.assertEqual(data["payment_method"], "card")
        self.assertEqual(data["status"], "pending")
        self.assertEqual(str(data["amount"]), "100.00")

    def test_payment_serializer_read_only_fields_ignored(self):
        serializer = PaymentSerializer(
            data={
                "booking": self.booking.id,
                "amount": "120.00",
                "currency": "NGN",
                "payment_method": "card",
                "tx_ref": "tx-readonly-001",
                "status": "succeeded",
            }
        )
        self.assertTrue(serializer.is_valid())
        self.assertNotIn("status", serializer.validated_data)

    def test_payment_serializer_rejects_invalid_payment_method(self):
        serializer = PaymentSerializer(
            data={
                "booking": self.booking.id,
                "amount": "120.00",
                "currency": "NGN",
                "payment_method": "cash",
                "tx_ref": "tx-invalid-001",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("payment_method", serializer.errors)

    def test_payment_serializer_rejects_invalid_amount(self):
        serializer = PaymentSerializer(
            data={
                "booking": self.booking.id,
                "amount": "not-a-number",
                "currency": "NGN",
                "payment_method": "card",
                "tx_ref": "tx-invalid-002",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)


class PaymentViewSetAuthTests(BasePaymentTestCase):
    def test_list_requires_auth(self):
        response = self.client.get(PAYMENTS_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_requires_auth(self):
        payment = self.create_payment()
        response = self.client.get(f"{PAYMENTS_URL}{payment.id}/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_requires_auth(self):
        booking = self.create_booking()
        response = self.client.post(
            PAYMENTS_URL,
            data={
                "booking": booking.id,
                "amount": "150.00",
                "currency": "NGN",
                "payment_method": "card",
                "tx_ref": "tx-auth-001",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PaymentViewSetListRetrieveTests(BasePaymentTestCase):
    def setUp(self):
        super().setUp()
        self.user_payment = self.create_payment(booking=self.create_booking(user=self.user))
        self.other_payment = self.create_payment(booking=self.create_booking(user=self.other_user))

    def test_regular_user_sees_only_own_payments(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(PAYMENTS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(self.user_payment.id))

    def test_admin_user_sees_all_payments(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(PAYMENTS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_regular_user_cannot_retrieve_other_payment(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{PAYMENTS_URL}{self.other_payment.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_user_can_retrieve_other_payment(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(f"{PAYMENTS_URL}{self.other_payment.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PaymentViewSetCreateUpdateDeleteTests(BasePaymentTestCase):
    def test_user_can_create_payment(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        response = self.client.post(
            PAYMENTS_URL,
            data={
                "booking": booking.id,
                "amount": "150.00",
                "currency": "NGN",
                "payment_method": "card",
                "tx_ref": "tx-create-001",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Payment.objects.count(), 1)

    def test_create_rejects_invalid_payment_method(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        response = self.client.post(
            PAYMENTS_URL,
            data={
                "booking": booking.id,
                "amount": "150.00",
                "currency": "NGN",
                "payment_method": "crypto",
                "tx_ref": "tx-create-002",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("payment_method", response.data)

    def test_user_can_update_own_payment(self):
        payment = self.create_payment()
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            f"{PAYMENTS_URL}{payment.id}/",
            data={"amount": "200.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(str(payment.amount), "200.00")

    def test_user_cannot_update_other_payment(self):
        payment = self.create_payment(booking=self.create_booking(user=self.other_user))
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            f"{PAYMENTS_URL}{payment.id}/",
            data={"amount": "200.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_delete_own_payment(self):
        payment = self.create_payment()
        self.client.force_authenticate(self.user)
        response = self.client.delete(f"{PAYMENTS_URL}{payment.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Payment.objects.filter(id=payment.id).exists())


class CardPaymentInitViewTests(BasePaymentTestCase):
    def test_card_init_requires_auth(self):
        response = self.client.post(CARD_INIT_URL, data={})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_card_init_requires_idempotency_key(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        response = self.client.post(
            CARD_INIT_URL,
            data={
                "booking_id": booking.id,
                "amount": "100.00",
                "currency": "NGN",
                "tx_ref": "tx-card-001",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_card_init_booking_not_found(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            CARD_INIT_URL,
            data={
                "booking_id": 999999,
                "amount": "100.00",
                "currency": "NGN",
                "tx_ref": "tx-card-002",
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="idem-card-001",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("app.payments.views.FlutterwaveService.initiate_card_payment")
    def test_card_init_idempotency_returns_existing_payment(self, mock_initiate):
        booking = self.create_booking()
        existing = self.create_payment(
            booking=booking,
            tx_ref="tx-card-003",
            idempotency_key="idem-card-002",
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(
            CARD_INIT_URL,
            data={
                "booking_id": booking.id,
                "amount": "100.00",
                "currency": "NGN",
                "tx_ref": "tx-card-003",
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="idem-card-002",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(existing.id))
        mock_initiate.assert_not_called()

    @patch("app.payments.views.FlutterwaveService.initiate_card_payment")
    def test_card_init_creates_payment_and_returns_gateway(self, mock_initiate):
        booking = self.create_booking()
        mock_initiate.return_value = {
            "link": "https://example.com/pay",
            "flw_ref": "FLW123",
            "tx_ref": "tx-card-004",
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(
            CARD_INIT_URL,
            data={
                "booking_id": booking.id,
                "amount": "100.00",
                "currency": "NGN",
                "tx_ref": "tx-card-004",
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="idem-card-003",
            HTTP_X_TRACE_ID="trace-123",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("payment", response.data)
        self.assertIn("gateway", response.data)
        payment = Payment.objects.get(id=response.data["payment"]["id"])
        self.assertEqual(payment.payment_method, "card")
        self.assertEqual(payment.idempotency_key, "idem-card-003")
        self.assertEqual(payment.trace_id, "trace-123")
        mock_initiate.assert_called_once_with(
            "100.00", "NGN", self.user.email, "tx-card-004"
        )


class BankTransferInitViewTests(BasePaymentTestCase):
    def test_bank_transfer_requires_auth(self):
        response = self.client.post(BANK_INIT_URL, data={})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_bank_transfer_requires_idempotency_key(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BANK_INIT_URL,
            data={"booking_id": booking.id, "amount": "120.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(
        STATIC_ACCOUNT_NAME="Test Account",
        STATIC_ACCOUNT_NUMBER="1234567890",
        STATIC_BANK_NAME="Test Bank",
    )
    def test_bank_transfer_creates_payment_and_returns_bank_details(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BANK_INIT_URL,
            data={"booking_id": booking.id, "amount": "120.00"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="idem-bank-001",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("payment", response.data)
        self.assertIn("bank_details", response.data)
        self.assertEqual(response.data["bank_details"]["bank_name"], "Test Bank")
        payment = Payment.objects.get(id=response.data["payment"]["id"])
        self.assertEqual(payment.payment_method, "bank_transfer")

    @override_settings(
        STATIC_ACCOUNT_NAME="Test Account",
        STATIC_ACCOUNT_NUMBER="1234567890",
        STATIC_BANK_NAME="Test Bank",
    )
    def test_bank_transfer_forces_currency_ngn(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        response = self.client.post(
            BANK_INIT_URL,
            data={"booking_id": booking.id, "amount": "120.00", "currency": "USD"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="idem-bank-002",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment = Payment.objects.get(id=response.data["payment"]["id"])
        self.assertEqual(payment.currency, "NGN")


class FlutterwaveWebhookTests(BasePaymentTestCase):
    def test_webhook_rejects_invalid_signature(self):
        response = self.client.post(
            WEBHOOK_URL,
            data={"txRef": "tx-webhook-001", "status": "successful"},
            format="json",
            HTTP_VERIF_HASH="invalid",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_webhook_requires_tx_ref(self):
        response = self.client.post(
            WEBHOOK_URL,
            data={"status": "successful"},
            format="json",
            HTTP_VERIF_HASH=settings.FLUTTERWAVE_SECRET_HASH,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_webhook_payment_not_found(self):
        response = self.client.post(
            WEBHOOK_URL,
            data={"txRef": "missing", "status": "successful"},
            format="json",
            HTTP_VERIF_HASH=settings.FLUTTERWAVE_SECRET_HASH,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_webhook_idempotent_already_processed(self):
        payment = self.create_payment(status="succeeded", tx_ref="tx-webhook-002")
        response = self.client.post(
            WEBHOOK_URL,
            data={"txRef": payment.tx_ref, "status": "successful"},
            format="json",
            HTTP_VERIF_HASH=settings.FLUTTERWAVE_SECRET_HASH,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Already processed")

    @patch("app.payments.views.process_flight_booking.delay")
    @patch("app.payments.views.BookingEngine.attach_payment")
    def test_webhook_successful_payment_updates_and_triggers_tasks(
        self, mock_attach, mock_delay
    ):
        payment = self.create_payment(tx_ref="tx-webhook-003")
        response = self.client.post(
            WEBHOOK_URL,
            data={
                "id": 123,
                "txRef": payment.tx_ref,
                "amount": "100.00",
                "currency": "NGN",
                "status": "successful",
            },
            format="json",
            HTTP_VERIF_HASH=settings.FLUTTERWAVE_SECRET_HASH,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "succeeded")
        self.assertEqual(payment.flutterwave_charge_id, "123")
        self.assertIsNotNone(payment.paid_at)
        mock_attach.assert_called_once_with(payment.booking, "confirmed")
        mock_delay.assert_called_once_with(str(payment.id))

    @patch("app.payments.views.BookingEngine.update_status")
    def test_webhook_failed_payment_marks_failed(self, mock_update):
        payment = self.create_payment(tx_ref="tx-webhook-004")
        response = self.client.post(
            WEBHOOK_URL,
            data={
                "id": 456,
                "txRef": payment.tx_ref,
                "amount": "100.00",
                "currency": "NGN",
                "status": "failed",
            },
            format="json",
            HTTP_VERIF_HASH=settings.FLUTTERWAVE_SECRET_HASH,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")
        mock_update.assert_called_once_with(payment.booking, "failed")


class PaymentVerificationTests(BasePaymentTestCase):
    def test_verification_requires_auth(self):
        response = self.client.post(VERIFY_URL, data={"tx_ref": "tx-verify-001"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verification_requires_tx_ref(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(VERIFY_URL, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verification_payment_not_found(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_URL, data={"tx_ref": "missing"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("app.payments.views.FlutterwaveService.verify_payment")
    def test_verification_already_verified(self, mock_verify):
        payment = self.create_payment(status="succeeded", tx_ref="tx-verify-002")
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_URL, data={"tx_ref": payment.tx_ref}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Already verified")
        mock_verify.assert_not_called()

    @patch("app.payments.views.FlutterwaveService.verify_payment")
    def test_verification_status_not_success(self, mock_verify):
        payment = self.create_payment(tx_ref="tx-verify-003")
        mock_verify.return_value = {"status": "error", "message": "bad"}
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_URL, data={"tx_ref": payment.tx_ref}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("app.payments.views.process_flight_booking.delay")
    @patch("app.payments.views.BookingEngine.attach_payment")
    @patch("app.payments.views.FlutterwaveService.verify_payment")
    def test_verification_successful_updates_payment(
        self, mock_verify, mock_attach, mock_delay
    ):
        payment = self.create_payment(amount=Decimal("100.00"), tx_ref="tx-verify-004")
        mock_verify.return_value = {
            "status": "success",
            "data": {
                "id": 999,
                "status": "successful",
                "amount": "100.00",
                "currency": "NGN",
            },
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_URL, data={"tx_ref": payment.tx_ref}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "succeeded")
        self.assertEqual(payment.flutterwave_charge_id, "999")
        self.assertIsNotNone(payment.paid_at)
        mock_attach.assert_called_once_with(payment.booking, "confirmed")
        mock_delay.assert_called_once_with(str(payment.id))

    @patch("app.payments.views.BookingEngine.update_status")
    @patch("app.payments.views.FlutterwaveService.verify_payment")
    def test_verification_mismatch_amount_or_currency(self, mock_verify, mock_update):
        payment = self.create_payment(amount=Decimal("100.00"), tx_ref="tx-verify-005")
        mock_verify.return_value = {
            "status": "success",
            "data": {
                "id": 888,
                "status": "successful",
                "amount": "120.00",
                "currency": "NGN",
            },
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(
            VERIFY_URL, data={"tx_ref": payment.tx_ref}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")
        mock_update.assert_called_once_with(payment.booking, "failed")


class PaymentRedirectTests(BasePaymentTestCase):
    def test_redirect_returns_status_and_reference(self):
        response = self.client.get(
            REDIRECT_URL,
            data={"tx_ref": "tx-redirect-001", "status": "successful"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode("utf-8")
        self.assertIn("tx-redirect-001", content)
        self.assertIn("successful", content)


class PaymentThrottleTests(BasePaymentTestCase):
    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_blocks_repeated_list_requests(self):
        self.create_payment()
        self.client.force_authenticate(self.user)
        first = self.client.get(PAYMENTS_URL)
        second = self.client.get(PAYMENTS_URL)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_blocks_repeated_create_requests(self):
        booking_one = self.create_booking()
        booking_two = self.create_booking()
        self.client.force_authenticate(self.user)
        first = self.client.post(
            PAYMENTS_URL,
            data={
                "booking": booking_one.id,
                "amount": "150.00",
                "currency": "NGN",
                "payment_method": "card",
                "tx_ref": "tx-throttle-001",
            },
            format="json",
        )
        second = self.client.post(
            PAYMENTS_URL,
            data={
                "booking": booking_two.id,
                "amount": "160.00",
                "currency": "NGN",
                "payment_method": "card",
                "tx_ref": "tx-throttle-002",
            },
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_separate_users_have_separate_limits(self):
        first_client = APIClient()
        second_client = APIClient()
        first_client.force_authenticate(self.user)
        second_client.force_authenticate(self.other_user)
        first = first_client.get(PAYMENTS_URL)
        second = second_client.get(PAYMENTS_URL)
        third = first_client.get(PAYMENTS_URL)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(third.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(REST_FRAMEWORK=throttled_settings("1/minute"))
    def test_throttle_cache_clear_resets_limits(self):
        self.client.force_authenticate(self.user)
        first = self.client.get(PAYMENTS_URL)
        second = self.client.get(PAYMENTS_URL)
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        cache.clear()
        third = self.client.get(PAYMENTS_URL)
        self.assertEqual(third.status_code, status.HTTP_200_OK)


class PaymentCachingTests(BasePaymentTestCase):
    def test_cache_store_and_retrieve_payment_list(self):
        payment = self.create_payment()
        data = PaymentSerializer([payment], many=True).data
        cache_key = f"payment_list:{self.user.id}"
        cache.set(cache_key, data, timeout=60)
        cached = cache.get(cache_key)
        self.assertEqual(cached, data)

    def test_cache_clear_removes_cached_entries(self):
        cache_key = f"payment_list:{self.user.id}"
        cache.set(cache_key, ["data"], timeout=60)
        cache.clear()
        self.assertIsNone(cache.get(cache_key))


class PaymentPerformanceTests(BasePaymentTestCase):
    def test_list_query_count_is_small(self):
        self.create_payment()
        self.client.force_authenticate(self.user)
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(PAYMENTS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(context), 3)

    def test_retrieve_query_count_is_small(self):
        payment = self.create_payment()
        self.client.force_authenticate(self.user)
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(f"{PAYMENTS_URL}{payment.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(context), 3)
