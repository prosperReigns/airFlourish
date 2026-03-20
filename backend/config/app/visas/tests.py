from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from app.bookings.models import Booking
from app.payments.models import Payment
from app.visas.models import VisaApplication, VisaDocument, VisaType


APPLICATIONS_URL = "/api/visas/applications/"
VISA_TYPES_URL = "/api/visas/visa-types/"


class VisaBaseTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        User = get_user_model()
        self.user = User.objects.create_user(
            email="visauser@example.com",
            password="password123",
            country="NG",
        )
        self.admin = User.objects.create_user(
            email="visaadmin@example.com",
            password="password123",
            country="NG",
            user_type="admin",
            is_staff=True,
        )
        self.agent = User.objects.create_user(
            email="visaagent@example.com",
            password="password123",
            country="NG",
            user_type="agent",
        )
        self.tourist = VisaType.objects.create(
            code="tourist",
            name="Tourist",
            country="NG",
            description="Tourist visa",
        )
        self.tourist.required_documents = ["passport"]
        self.tourist.save(update_fields=["required_documents"])


class VisaTypeTests(VisaBaseTestCase):
    def test_list_visa_types_requires_auth(self):
        response = self.client.get(f"{VISA_TYPES_URL}?country=NG")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_visa_types_returns_required_docs(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"{VISA_TYPES_URL}?country=NG")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", {})
        visa_types = results.get("visa_types", [])
        self.assertTrue(visa_types)
        self.assertIn("required_documents", visa_types[0])
        self.assertTrue(visa_types[0]["required_documents"])


class VisaApplicationFlowTests(VisaBaseTestCase):
    def test_create_requires_auth(self):
        response = self.client.post(APPLICATIONS_URL, data={})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_application_with_visa_type(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            APPLICATIONS_URL, {"visa_type": "tourist"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        app = VisaApplication.objects.get(id=response.data["id"])
        self.assertEqual(app.visa_type.code, "tourist")

    def test_documents_validation(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            APPLICATIONS_URL, {"visa_type": "tourist"}, format="json"
        )
        app_id = response.data["id"]

        # invalid document type
        invalid = self.client.post(
            f"{APPLICATIONS_URL}{app_id}/documents/",
            {"document_type": "invalid_doc"},
            format="multipart",
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_agent_can_create_application_for_user(self):
        self.client.force_authenticate(self.agent)
        response = self.client.post(
            APPLICATIONS_URL,
            {"visa_type": "tourist", "user": self.user.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        application = VisaApplication.objects.get(id=response.data["id"])
        self.assertEqual(application.user_id, self.user.id)
        self.assertEqual(application.agent_id, self.agent.id)

    def test_document_quality_validation_and_correction_loop(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            APPLICATIONS_URL, {"visa_type": "tourist"}, format="json"
        )
        app_id = response.data["id"]
        application = VisaApplication.objects.get(id=app_id)
        VisaDocument.objects.create(
            application=application,
            document_type="passport",
            file=SimpleUploadedFile("passport.pdf", b""),
        )

        validate = self.client.post(f"{APPLICATIONS_URL}{app_id}/validate/")
        self.assertEqual(validate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("document_quality", validate.data.get("errors", {}))
        application.refresh_from_db()
        self.assertEqual(application.status, VisaApplication.STATUS_DRAFT)

        self.client.post(
            f"{APPLICATIONS_URL}{app_id}/documents/",
            {
                "document_type": "passport",
                "file": SimpleUploadedFile("passport.pdf", b"valid-content"),
            },
            format="multipart",
        )
        validate = self.client.post(f"{APPLICATIONS_URL}{app_id}/validate/")
        self.assertEqual(validate.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.status, VisaApplication.STATUS_READY_FOR_SUBMISSION)

    def test_internal_notes_admin_only(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            APPLICATIONS_URL, {"visa_type": "tourist"}, format="json"
        )
        app_id = response.data["id"]

        update = self.client.patch(
            f"{APPLICATIONS_URL}{app_id}/",
            {"internal_notes": "Internal review note"},
            format="json",
        )
        self.assertEqual(update.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.admin)
        update = self.client.patch(
            f"{APPLICATIONS_URL}{app_id}/",
            {"internal_notes": "Internal review note"},
            format="json",
        )
        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data.get("internal_notes"), "Internal review note")

    @patch("app.visas.views.FlutterwaveService.initiate_card_payment")
    def test_pay_requires_ready_for_submission(self, mock_init):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            APPLICATIONS_URL, {"visa_type": "tourist"}, format="json"
        )
        app_id = response.data["id"]

        pay = self.client.post(
            f"{APPLICATIONS_URL}{app_id}/pay/",
            {"amount": 200, "currency": "NGN"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="visa-001",
        )
        self.assertEqual(pay.status_code, status.HTTP_400_BAD_REQUEST)

        # Upload required document and validate
        self.client.post(
            f"{APPLICATIONS_URL}{app_id}/documents/",
            {
                "document_type": "passport",
                "file": SimpleUploadedFile("passport.pdf", b"valid-content"),
            },
            format="multipart",
        )
        validate = self.client.post(f"{APPLICATIONS_URL}{app_id}/validate/")
        self.assertEqual(validate.status_code, status.HTTP_200_OK)

        mock_init.return_value = {"status": "success", "data": {"link": "https://pay.test"}}
        pay = self.client.post(
            f"{APPLICATIONS_URL}{app_id}/pay/",
            {"amount": 200, "currency": "NGN"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="visa-001",
        )
        self.assertEqual(pay.status_code, status.HTTP_201_CREATED)
        self.assertIn("payment_link", pay.data)

    def test_embassy_review_flow(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            APPLICATIONS_URL, {"visa_type": "tourist"}, format="json"
        )
        app_id = response.data["id"]
        self.client.post(
            f"{APPLICATIONS_URL}{app_id}/documents/",
            {
                "document_type": "passport",
                "file": SimpleUploadedFile("passport.pdf", b"valid-content"),
            },
            format="multipart",
        )
        validate = self.client.post(f"{APPLICATIONS_URL}{app_id}/validate/")
        self.assertEqual(validate.status_code, status.HTTP_200_OK)

        application = VisaApplication.objects.get(id=app_id)
        booking = Booking.objects.create(
            user=self.user,
            service_type="visa",
            reference_code="visa-embassy-001",
            total_price=200,
            currency="NGN",
        )
        application.booking = booking
        application.save(update_fields=["booking", "updated_at"])
        Payment.objects.create(
            booking=booking,
            tx_ref="visa-pay-001",
            amount=200,
            currency="NGN",
            payment_method="card",
            status="succeeded",
        )

        submit = self.client.post(f"{APPLICATIONS_URL}{app_id}/submit/")
        self.assertEqual(submit.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.admin)
        review = self.client.post(f"{APPLICATIONS_URL}{app_id}/review/")
        self.assertEqual(review.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.status, VisaApplication.STATUS_UNDER_EMBASSY_REVIEW)

        approve = self.client.post(f"{APPLICATIONS_URL}{app_id}/approve/")
        self.assertEqual(approve.status_code, status.HTTP_200_OK)
        application.refresh_from_db()
        self.assertEqual(application.status, VisaApplication.STATUS_APPROVED)
