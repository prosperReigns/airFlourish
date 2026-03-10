import requests
from django.conf import settings


class FlutterwaveService:
    BASE_URL = "https://api.flutterwave.com/v3"

    def __init__(self):
        """Initializes the FlutterwaveService with the necessary configuration. This includes setting the secret key for authentication and preparing the headers for API requests. The secret key is retrieved from the Django settings, and the headers include the Authorization token and Content-Type for JSON requests.
        Expected configuration in settings.py:
        FLUTTERWAVE_SECRET_KEY = "your_secret_key_here"
        """
        self.secret_key = settings.FLUTTERWAVE_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }

    # -------------------------
    # INITIATE CARD PAYMENT
    # -------------------------
    def initiate_card_payment(self, amount, currency, customer_email, tx_ref):
        """Initiates a card payment with Flutterwave. This method sends a POST request to the Flutterwave API to create a new payment transaction. The amount, currency, customer email, and transaction reference are required parameters. The method returns the response from Flutterwave, which includes the payment link for the customer to complete the payment.
        Expected input:
        {
            "amount": 100.00,"
            "currency": "USD",
            "customer_email": "customer@example.com",
            "tx_ref": "unique_transaction_reference"
        }
        """

        url = f"{self.BASE_URL}/payments"

        payload = {
            "tx_ref": tx_ref,
            "amount": str(amount),
            "currency": currency,
            "payment_options": "card",
            "customer": {"email": customer_email},
            "redirect_url": settings.PAYMENT_REDIRECT_URL,
        }

        response = requests.post(
            url,
            json=payload,
            headers=self.headers,
            timeout=30
        )

        return self._handle_response(response)

    # -------------------------
    # VERIFY PAYMENT
    # -------------------------
    def verify_payment(self, tx_ref):
        """Verifies the status of a payment transaction with Flutterwave. This method sends a GET request to the Flutterwave API to check the status of a payment using the transaction reference. The method returns the response from Flutterwave, which includes the payment status and other relevant details.
        Expected input:
        {
            "tx_ref": "unique_transaction_reference"
        }
        """

        url = f"{self.BASE_URL}/transactions/verify_by_reference"
        params = {"tx_ref": tx_ref}

        response = requests.get(
            url,
            params=params,
            headers=self.headers,
            timeout=30
        )

        return self._handle_response(response)

    # -------------------------
    # REFUND PAYMENT
    # -------------------------
    def refund_payment(self, transaction_id):
        """Initiates a refund for a payment transaction with Flutterwave. This method sends a POST request to the Flutterwave API to create a refund for a specific transaction using its ID. The method returns the response from Flutterwave, which includes the refund status and other relevant details.
        Expected input:
        {
            "transaction_id": "flutterwave_transaction_id"
        }
        """

        url = f"{self.BASE_URL}/transactions/{transaction_id}/refund"

        response = requests.post(
            url,
            headers=self.headers,
            timeout=30
        )

        return self._handle_response(response)

    # -------------------------
    # INTERNAL RESPONSE HANDLER
    # -------------------------
    def _handle_response(self, response):
        """Handles the response from Flutterwave API. This method attempts to parse the JSON response and checks the HTTP status code. If the response is not successful (status code not in 200 or 201), it returns an error message with the status code. If the response is successful, it returns the parsed JSON data.
        Expected input: Response object from requests library
        Expected output:
        {
            "status": "success",
            "message": "Payment initiated successfully",
            "data": {
                // payment details from Flutterwave
            }
        }
        or
        {
            "status": "error",
            "message": "Error message from Flutterwave",
            "http_status": 400
        }
        """

        try:
            data = response.json()
        except ValueError:
            return {
                "status": "error",
                "message": "Invalid JSON response from Flutterwave",
                "http_status": response.status_code
            }

        if response.status_code not in [200, 201]:
            return {
                "status": "error",
                "message": data,
                "http_status": response.status_code
            }

        return data