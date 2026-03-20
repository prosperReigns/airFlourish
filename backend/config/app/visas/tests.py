from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from app.visas.models import VisaApplication, VisaType


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
        self.tourist = VisaType.objects.create(
            code="tourist",
            name="Tourist",
            country="NG",
            description="Tourist visa",
        )


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

    @patch("app.visas.views.FlutterwaveService.initiate_card_payment")
    def test_checkout_requires_ready_for_payment(self, mock_init):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            APPLICATIONS_URL, {"visa_type": "tourist"}, format="json"
        )
        app_id = response.data["id"]

        checkout = self.client.post(
            f"{APPLICATIONS_URL}{app_id}/checkout/",
            {"amount": 200, "currency": "NGN"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="visa-001",
        )
        self.assertEqual(checkout.status_code, status.HTTP_400_BAD_REQUEST)

        # Upload required document and validate
        self.client.post(
            f"{APPLICATIONS_URL}{app_id}/documents/",
            {"document_type": "passport"},
            format="multipart",
        )
        validate = self.client.post(f"{APPLICATIONS_URL}{app_id}/validate/")
        self.assertEqual(validate.status_code, status.HTTP_200_OK)

        mock_init.return_value = {"status": "success", "data": {"link": "https://pay.test"}}
        checkout = self.client.post(
            f"{APPLICATIONS_URL}{app_id}/checkout/",
            {"amount": 200, "currency": "NGN"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="visa-001",
        )
        self.assertEqual(checkout.status_code, status.HTTP_201_CREATED)
        self.assertIn("payment_link", checkout.data)
