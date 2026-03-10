from celery import shared_task
from app.services.amadeus import AmadeusService
from app.services.booking_engine import BookingEngine
from app.payments.models import Payment
from app.services.flutterwave import FlutterwaveService

@shared_task(bind=True, max_retries=3)
def process_flight_booking(self, payment_id):
    try:
        payment = Payment.objects.get(id=payment_id)

        if payment.status != "successful":
            return "Payment not successful"

        meta = payment.raw_response.get("meta", {})
        flight_offer = meta.get("flight_offer")
        travelers = meta.get("travelers")

        # Call Amadeus
        flight_order = AmadeusService.create_flight_order(
            flight_offer,
            travelers
        )

        # Create unified booking
        booking = BookingEngine.create_booking(
            user=payment.booking.user,
            service_type="flight",
            total_price=payment.amount,
            currency=payment.booking.currency,
            external_service_id=flight_order["id"]
        )

        payment.booking = booking
        payment.status = "booking_created"
        payment.save()

        BookingEngine.update_status(booking, "confirmed")

        return "Flight booked successfully"

    except Exception as e:
        # Refund on failure
        FlutterwaveService().refund_payment(payment.transaction_id)
        payment.status = "refunded"
        payment.save()

        raise self.retry(exc=e, countdown=60)