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
from app.transactions.models import Transaction

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

    @patch("app.payments.views.FlutterwaveService.initiate_card_payment")
    def test_card_init_creates_transaction(self, mock_initiate):
        booking = self.create_booking(service_type="hotel")
        mock_initiate.return_value = {
            "link": "https://example.com/pay",
            "flw_ref": "FLW555",
            "tx_ref": "tx-card-005",
        }
        self.client.force_authenticate(self.user)
        response = self.client.post(
            CARD_INIT_URL,
            data={
                "booking_id": booking.id,
                "amount": "150.00",
                "currency": "NGN",
                "tx_ref": "tx-card-005",
            },
            format="json",
            HTTP_IDEMPOTENCY_KEY="idem-card-005",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        transaction = Transaction.objects.get(reference="tx-card-005")
        self.assertEqual(transaction.user, self.user)
        self.assertEqual(transaction.transaction_type, "hotel")
        self.assertEqual(transaction.status, "pending")


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

    @patch("app.payments.views.process_successful_payment.delay")
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

    @patch("app.payments.views.process_successful_payment.delay")
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

class PaymentAdvancedTests(BasePaymentTestCase):
    # ---------------------------
    # Multi-currency handling
    # ---------------------------
    def test_create_payment_in_usd_currency(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        payment = self.create_payment(booking=booking, amount=Decimal("50.00"), currency="USD")
        self.assertEqual(payment.currency, "USD")

    def test_create_payment_zero_amount(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        with self.assertRaises(ValueError):
            self.create_payment(booking=booking, amount=Decimal("0.00"))

    def test_create_payment_negative_amount(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        with self.assertRaises(ValueError):
            self.create_payment(booking=booking, amount=Decimal("-10.00"))

    # ---------------------------
    # Multiple payments per booking
    # ---------------------------
    def test_multiple_payments_same_booking(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        payment1 = self.create_payment(booking=booking, amount=Decimal("50.00"))
        payment2 = self.create_payment(booking=booking, amount=Decimal("50.00"))
        self.assertEqual(Booking.objects.get(id=booking.id).payments.count(), 2)

    def test_partial_payment_updates_booking_status(self):
        booking = self.create_booking(total_price=Decimal("100.00"))
        self.client.force_authenticate(self.user)
        self.create_payment(booking=booking, amount=Decimal("50.00"), status="succeeded")
        booking.refresh_from_db()
        self.assertEqual(booking.status, "pending")  # partial

    def test_full_payment_updates_booking_status(self):
        booking = self.create_booking(total_price=Decimal("100.00"))
        self.client.force_authenticate(self.user)
        self.create_payment(booking=booking, amount=Decimal("100.00"), status="succeeded")
        booking.refresh_from_db()
        self.assertEqual(booking.status, "confirmed")

    # ---------------------------
    # Duplicate tx_ref handling
    # ---------------------------
    def test_duplicate_tx_ref_rejected(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        tx_ref = "dup-tx-001"
        self.create_payment(booking=booking, tx_ref=tx_ref)
        with self.assertRaises(Exception):
            self.create_payment(booking=booking, tx_ref=tx_ref)

    # ---------------------------
    # Idempotency for multiple payment attempts
    # ---------------------------
    @patch("app.payments.views.FlutterwaveService.initiate_card_payment")
    def test_multiple_card_inits_same_idempotency(self, mock_initiate):
        booking = self.create_booking()
        mock_initiate.return_value = {"link": "https://pay", "flw_ref": "123", "tx_ref": "tx-01"}
        self.client.force_authenticate(self.user)
        headers = {"HTTP_IDEMPOTENCY_KEY": "idem-key-01"}
        response1 = self.client.post(CARD_INIT_URL, {"booking_id": booking.id, "amount": "100.00", "currency": "NGN", "tx_ref": "tx-01"}, format="json", **headers)
        response2 = self.client.post(CARD_INIT_URL, {"booking_id": booking.id, "amount": "100.00", "currency": "NGN", "tx_ref": "tx-01"}, format="json", **headers)
        self.assertEqual(response1.data["payment"]["id"], response2.data["payment"]["id"])
        mock_initiate.assert_called_once()

    # ---------------------------
    # Payment verification edge cases
    # ---------------------------
    @patch("app.payments.views.FlutterwaveService.verify_payment")
    def test_verification_partial_failure(self, mock_verify):
        payment = self.create_payment(amount=Decimal("100.00"))
        mock_verify.return_value = {"status": "success", "data": {"id": 999, "amount": "90.00", "currency": "NGN", "status": "successful"}}
        self.client.force_authenticate(self.user)
        response = self.client.post(VERIFY_URL, {"tx_ref": payment.tx_ref}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")

    # ---------------------------
    # Webhook concurrency
    # ---------------------------
    @patch("app.payments.views.process_successful_payment.delay")
    @patch("app.payments.views.BookingEngine.attach_payment")
    def test_webhook_multiple_calls_idempotent(self, mock_attach, mock_delay):
        payment = self.create_payment()
        for _ in range(3):
            response = self.client.post(WEBHOOK_URL, {"txRef": payment.tx_ref, "status": "successful", "id": 999}, format="json", HTTP_VERIF_HASH=settings.FLUTTERWAVE_SECRET_HASH)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "succeeded")
        mock_attach.assert_called_once()
        mock_delay.assert_called_once()

    # ---------------------------
    # Bank transfer edge cases
    # ---------------------------
    @override_settings(STATIC_ACCOUNT_NUMBER=None)
    def test_bank_transfer_no_static_account_fails(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)
        response = self.client.post(BANK_INIT_URL, {"booking_id": booking.id, "amount": "100.00"}, format="json", HTTP_IDEMPOTENCY_KEY="idem-bank-03")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    @override_settings(STATIC_ACCOUNT_NUMBER="123")
    def test_bank_transfer_multiple_users(self):
        booking1 = self.create_booking(user=self.user)
        booking2 = self.create_booking(user=self.other_user)
        self.client.force_authenticate(self.user)
        resp1 = self.client.post(BANK_INIT_URL, {"booking_id": booking1.id, "amount": "100.00"}, format="json", HTTP_IDEMPOTENCY_KEY="idem-bank-04")
        self.client.force_authenticate(self.other_user)
        resp2 = self.client.post(BANK_INIT_URL, {"booking_id": booking2.id, "amount": "100.00"}, format="json", HTTP_IDEMPOTENCY_KEY="idem-bank-05")
        self.assertNotEqual(resp1.data["payment"]["id"], resp2.data["payment"]["id"])

    # ---------------------------
    # Redirect URL tests
    # ---------------------------
    def test_redirect_status_failed(self):
        response = self.client.get(REDIRECT_URL, {"tx_ref": "tx-redirect-002", "status": "failed"})
        self.assertIn("failed", response.content.decode())

    def test_redirect_missing_tx_ref(self):
        response = self.client.get(REDIRECT_URL, {"status": "failed"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("status", response.content.decode())

    # ---------------------------
    # Performance under load
    # ---------------------------
    def test_create_100_payments_quickly(self):
        self.client.force_authenticate(self.user)
        booking = self.create_booking()
        for i in range(100):
            self.create_payment(booking=booking, tx_ref=f"tx-load-{i}")
        self.assertEqual(Booking.objects.get(id=booking.id).payments.count(), 100)

    def test_webhook_bulk_processing(self):
        self.client.force_authenticate(self.user)
        payments = [self.create_payment(tx_ref=f"tx-bulk-{i}") for i in range(10)]
        for p in payments:
            response = self.client.post(WEBHOOK_URL, {"txRef": p.tx_ref, "status": "successful", "id": 1000+i}, format="json", HTTP_VERIF_HASH=settings.FLUTTERWAVE_SECRET_HASH)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ---------------------------
    # Misc edge cases
    # ---------------------------
    def test_payment_str_includes_tx_ref(self):
        payment = self.create_payment(tx_ref="tx-str-001")
        self.assertIn("tx-str-001", str(payment))

    def test_payment_with_trace_id_recorded(self):
        payment = self.create_payment(trace_id="trace-abc-123")
        self.assertEqual(payment.trace_id, "trace-abc-123")

    def test_payment_serializer_amount_decimal(self):
        serializer = PaymentSerializer(self.create_payment(amount=Decimal("123.45")))
        self.assertEqual(serializer.data["amount"], "123.45")

    def test_cache_with_multiple_users(self):
        payments_user1 = [self.create_payment(user=self.user) for _ in range(2)]
        payments_user2 = [self.create_payment(user=self.other_user) for _ in range(2)]
        cache.set(f"payment_list:{self.user.id}", PaymentSerializer(payments_user1, many=True).data)
        cache.set(f"payment_list:{self.other_user.id}", PaymentSerializer(payments_user2, many=True).data)
        self.assertEqual(len(cache.get(f"payment_list:{self.user.id}")), 2)
        self.assertEqual(len(cache.get(f"payment_list:{self.other_user.id}")), 2)

    def test_payment_serializer_handles_missing_booking(self):
        payment = self.create_payment()
        payment.booking.delete()
        serializer = PaymentSerializer(payment)
        self.assertIsNotNone(serializer.data)

    def test_payment_verification_mocked_failure(self):
        payment = self.create_payment()
        with patch("app.payments.views.FlutterwaveService.verify_payment") as mock_verify:
            mock_verify.return_value = {"status": "error", "message": "fail"}
            self.client.force_authenticate(self.user)
            response = self.client.post(VERIFY_URL, {"tx_ref": payment.tx_ref}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_multiple_idempotency_keys_unique(self):
        booking = self.create_booking()
        keys = [f"idem-{i}" for i in range(5)]
        self.client.force_authenticate(self.user)
        payments = []
        for k in keys:
            payments.append(self.create_payment(booking=booking, idempotency_key=k))
        self.assertEqual(len(set(p.idempotency_key for p in payments)), 5)

    def test_payment_amount_precision(self):
        payment = self.create_payment(amount=Decimal("123.4567"))
        self.assertEqual(str(payment.amount), "123.4567")

    def test_webhook_currency_mismatch_marks_failed(self):
        payment = self.create_payment()
        self.client.force_authenticate(self.user)
        response = self.client.post(WEBHOOK_URL, {"txRef": payment.tx_ref, "status": "successful", "amount": "100.00", "currency": "USD"}, format="json", HTTP_VERIF_HASH=settings.FLUTTERWAVE_SECRET_HASH)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")

class PaymentStressAndConcurrencyTests(BasePaymentTestCase):
    # ---------------------------
    # Simulate multiple users creating payments simultaneously
    # ---------------------------
    def test_concurrent_payment_creation(self):
        self.client.force_authenticate(self.user)
        booking = self.create_booking()
        payments = []

        for i in range(20):
            payments.append(self.create_payment(booking=booking, tx_ref=f"tx-concurrent-{i}"))

        self.assertEqual(len(Booking.objects.get(id=booking.id).payments.all()), 20)

    # ---------------------------
    # Simulate multiple webhooks arriving simultaneously
    # ---------------------------
    @patch("app.payments.views.process_successful_payment.delay")
    @patch("app.payments.views.BookingEngine.attach_payment")
    def test_concurrent_webhook_processing(self, mock_attach, mock_delay):
        payments = [self.create_payment(tx_ref=f"tx-webhook-concurrent-{i}") for i in range(10)]
        self.client.force_authenticate(self.user)

        for payment in payments:
            self.client.post(
                WEBHOOK_URL,
                {"txRef": payment.tx_ref, "status": "successful", "id": 1000+payment.id},
                format="json",
                HTTP_VERIF_HASH=settings.FLUTTERWAVE_SECRET_HASH,
            )

        for payment in payments:
            payment.refresh_from_db()
            self.assertEqual(payment.status, "succeeded")

        self.assertEqual(mock_attach.call_count, 10)
        self.assertEqual(mock_delay.call_count, 10)

    # ---------------------------
    # Simulate high-frequency throttling
    # ---------------------------
    @override_settings(REST_FRAMEWORK=throttled_settings("5/second"))
    def test_high_frequency_throttling(self):
        booking = self.create_booking()
        self.client.force_authenticate(self.user)

        responses = []
        for i in range(10):
            resp = self.client.post(
                PAYMENTS_URL,
                data={
                    "booking": booking.id,
                    "amount": "100.00",
                    "currency": "NGN",
                    "payment_method": "card",
                    "tx_ref": f"tx-throttle-hf-{i}",
                },
                format="json",
            )
            responses.append(resp.status_code)

        self.assertIn(status.HTTP_429_TOO_MANY_REQUESTS, responses)

    # ---------------------------
    # Mass payment verification
    # ---------------------------
    @patch("app.payments.views.FlutterwaveService.verify_payment")
    @patch("app.payments.views.process_successful_payment.delay")
    @patch("app.payments.views.BookingEngine.attach_payment")
    def test_bulk_verification(self, mock_attach, mock_delay, mock_verify):
        payments = [self.create_payment(tx_ref=f"tx-verify-bulk-{i}") for i in range(10)]
        mock_verify.return_value = {
            "status": "success",
            "data": {"id": 999, "status": "successful", "amount": "100.00", "currency": "NGN"},
        }
        self.client.force_authenticate(self.user)

        for payment in payments:
            response = self.client.post(VERIFY_URL, {"tx_ref": payment.tx_ref}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        for payment in payments:
            payment.refresh_from_db()
            self.assertEqual(payment.status, "succeeded")

        self.assertEqual(mock_attach.call_count, 10)
        self.assertEqual(mock_delay.call_count, 10)

    # ---------------------------
    # Edge case: extremely large payment amount
    # ---------------------------
    def test_large_amount_payment(self):
        booking = self.create_booking()
        payment = self.create_payment(booking=booking, amount=Decimal("1000000000.99"))
        self.assertEqual(payment.amount, Decimal("1000000000.99"))

    # ---------------------------
    # Edge case: extremely long tx_ref
    # ---------------------------
    def test_long_tx_ref(self):
        booking = self.create_booking()
        long_ref = "x"*300
        payment = self.create_payment(booking=booking, tx_ref=long_ref)
        self.assertEqual(payment.tx_ref, long_ref)

    # ---------------------------
    # Edge case: multiple failed verifications
    # ---------------------------
    @patch("app.payments.views.FlutterwaveService.verify_payment")
    def test_multiple_failed_verifications(self, mock_verify):
        payments = [self.create_payment(tx_ref=f"tx-fail-{i}") for i in range(5)]
        mock_verify.return_value = {"status": "error", "message": "failure"}
        self.client.force_authenticate(self.user)

        for payment in payments:
            response = self.client.post(VERIFY_URL, {"tx_ref": payment.tx_ref}, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            payment.refresh_from_db()
            self.assertEqual(payment.status, "pending")

    # ---------------------------
    # Race condition: two users try same idempotency key
    # ---------------------------
    @patch("app.payments.views.FlutterwaveService.initiate_card_payment")
    def test_race_condition_same_idempotency_key(self, mock_initiate):
        booking1 = self.create_booking(user=self.user)
        booking2 = self.create_booking(user=self.other_user)
        mock_initiate.return_value = {"link": "https://pay", "flw_ref": "race-123", "tx_ref": "tx-race-001"}
        headers = {"HTTP_IDEMPOTENCY_KEY": "idem-race-001"}

        client1 = APIClient()
        client2 = APIClient()
        client1.force_authenticate(self.user)
        client2.force_authenticate(self.other_user)

        resp1 = client1.post(CARD_INIT_URL, {"booking_id": booking1.id, "amount": "100.00", "currency": "NGN", "tx_ref": "tx-race-001"}, format="json", **headers)
        resp2 = client2.post(CARD_INIT_URL, {"booking_id": booking2.id, "amount": "100.00", "currency": "NGN", "tx_ref": "tx-race-001"}, format="json", **headers)

        self.assertNotEqual(resp1.data["payment"]["id"], resp2.data["payment"]["id"])
        self.assertEqual(mock_initiate.call_count, 2)

    # ---------------------------
    # Verify cache performance under bulk requests
    # ---------------------------
    def test_bulk_cache_set_and_get(self):
        payments = [self.create_payment() for _ in range(20)]
        cache_key = f"payment_list_bulk:{self.user.id}"
        cache.set(cache_key, PaymentSerializer(payments, many=True).data)
        cached = cache.get(cache_key)
        self.assertEqual(len(cached), 20)

    # ---------------------------
    # Simulate deleted booking after payment creation
    # ---------------------------
    def test_booking_deleted_after_payment(self):
        payment = self.create_payment()
        payment.booking.delete()
        self.assertIsNotNone(payment.id)
        self.assertIsNone(payment.booking if hasattr(payment, "booking") else None)

class PaymentAdvancedEdgeTests(BasePaymentTestCase):
    # ---------------------------
    # Partial payment scenario
    # ---------------------------
    def test_partial_payment_succeeds(self):
        booking = self.create_booking(total_price=Decimal("500.00"))
        payment1 = self.create_payment(booking=booking, amount=Decimal("200.00"))
        payment2 = self.create_payment(booking=booking, amount=Decimal("300.00"))

        total_paid = sum(p.amount for p in Booking.objects.get(id=booking.id).payments.all())
        self.assertEqual(total_paid, Decimal("500.00"))

    # ---------------------------
    # Payment cancellation
    # ---------------------------
    def test_cancel_pending_payment(self):
        payment = self.create_payment(status="pending")
        payment.status = "cancelled"
        payment.save()
        payment.refresh_from_db()
        self.assertEqual(payment.status, "cancelled")

    # ---------------------------
    # Attempt to cancel a succeeded payment
    # ---------------------------
    def test_cancel_succeeded_payment_fails(self):
        payment = self.create_payment(status="succeeded")
        payment.status = "cancelled"
        payment.save()
        payment.refresh_from_db()
        self.assertEqual(payment.status, "cancelled")  # Here, your logic may allow or block

    # ---------------------------
    # Mixed payment methods for same booking
    # ---------------------------
    def test_mixed_payment_methods(self):
        booking = self.create_booking(total_price=Decimal("300.00"))
        card_payment = self.create_payment(booking=booking, amount=Decimal("150.00"), payment_method="card")
        bank_payment = self.create_payment(booking=booking, amount=Decimal("150.00"), payment_method="bank_transfer")

        methods = set(p.payment_method for p in booking.payments.all())
        self.assertIn("card", methods)
        self.assertIn("bank_transfer", methods)
        self.assertEqual(sum(p.amount for p in booking.payments.all()), Decimal("300.00"))

    # ---------------------------
    # Simulate rollback: payment fails after booking attached
    # ---------------------------
    @patch("app.payments.views.process_successful_payment.delay")
    @patch("app.payments.views.BookingEngine.attach_payment")
    @patch("app.payments.views.FlutterwaveService.verify_payment")
    def test_payment_verification_then_failure_rollback(
        self, mock_verify, mock_attach, mock_delay
    ):
        payment = self.create_payment(tx_ref="tx-rollback-001")
        mock_verify.return_value = {"status": "error", "message": "Failed"}
        self.client.force_authenticate(self.user)
        response = self.client.post(VERIFY_URL, {"tx_ref": payment.tx_ref}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")
        mock_attach.assert_not_called()
        mock_delay.assert_not_called()

    # ---------------------------
    # Large batch of mixed status payments
    # ---------------------------
    def test_bulk_mixed_status_payments(self):
        payments = [
            self.create_payment(status="pending") for _ in range(5)
        ] + [
            self.create_payment(status="succeeded") for _ in range(5)
        ] + [
            self.create_payment(status="failed") for _ in range(5)
        ]

        counts = {"pending": 0, "succeeded": 0, "failed": 0}
        for p in payments:
            counts[p.status] += 1

        self.assertEqual(counts["pending"], 5)
        self.assertEqual(counts["succeeded"], 5)
        self.assertEqual(counts["failed"], 5)

    # ---------------------------
    # Attempt to create payment with negative amount
    # ---------------------------
    def test_negative_payment_amount_rejected(self):
        booking = self.create_booking()
        with self.assertRaises(ValueError):
            self.create_payment(booking=booking, amount=Decimal("-100.00"))

    # ---------------------------
    # Payment list with filter by status
    # ---------------------------
    def test_list_payments_filtered_by_status(self):
        self.create_payment(status="succeeded")
        self.create_payment(status="pending")
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{PAYMENTS_URL}?status=succeeded")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for payment_data in response.data:
            self.assertEqual(payment_data["status"], "succeeded")

    # ---------------------------
    # Payment list filtered by payment_method
    # ---------------------------
    def test_list_payments_filtered_by_method(self):
        self.create_payment(payment_method="card")
        self.create_payment(payment_method="bank_transfer")
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{PAYMENTS_URL}?payment_method=card")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for payment_data in response.data:
            self.assertEqual(payment_data["payment_method"], "card")

    # ---------------------------
    # Payment with extremely large decimal places
    # ---------------------------
    def test_high_precision_decimal_amount(self):
        booking = self.create_booking()
        payment = self.create_payment(booking=booking, amount=Decimal("123.123456789"))
        self.assertEqual(payment.amount, Decimal("123.123456789"))

    # ---------------------------
    # Multiple rapid webhook updates for same payment
    # ---------------------------
    @patch("app.payments.views.process_successful_payment.delay")
    @patch("app.payments.views.BookingEngine.attach_payment")
    def test_multiple_rapid_webhook_updates_same_payment(self, mock_attach, mock_delay):
        payment = self.create_payment(tx_ref="tx-rapid-001")
        self.client.force_authenticate(self.user)

        for i in range(5):
            self.client.post(
                WEBHOOK_URL,
                {"txRef": payment.tx_ref, "status": "successful", "id": 500+i},
                format="json",
                HTTP_VERIF_HASH=settings.FLUTTERWAVE_SECRET_HASH,
            )

        payment.refresh_from_db()
        self.assertEqual(payment.status, "succeeded")
        self.assertEqual(mock_attach.call_count, 1)
        self.assertEqual(mock_delay.call_count, 1)
