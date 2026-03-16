from celery import shared_task

from app.flights.models import FlightBooking
from app.payments.models import Payment
from app.services.amadeus import AmadeusService
from app.services.booking_engine import BookingEngine
from app.services.flutterwave import FlutterwaveService


def process_flight_booking_logic(payment):
    booking = payment.booking
    meta = (payment.raw_response or {}).get("meta", {})
    flight_offer = meta.get("flight_offer")
    travelers = meta.get("travelers")

    if not flight_offer or not travelers:
        raise ValueError("Missing flight_offer or travelers in payment metadata")

    # Call Amadeus
    flight_order = AmadeusService.create_flight_order(
        flight_offer,
        travelers,
    )

    booking.external_service_id = flight_order.get("id")
    booking.save(update_fields=["external_service_id"])

    BookingEngine.update_status(booking, "confirmed")

    FlightBooking.objects.get_or_create(
        booking=booking,
        defaults={
            "departure_city": meta.get("departure_city", ""),
            "arrival_city": meta.get("arrival_city", ""),
            "departure_date": meta.get("departure_date"),
            "return_date": meta.get("return_date"),
            "airline": meta.get("airline", ""),
            "passengers": meta.get("passengers", 1),
        },
    )

@shared_task(bind=True, max_retries=3)
def process_flight_booking(self, payment_id):
    try:
        payment = Payment.objects.select_related("booking").get(id=payment_id)

        if payment.status != "succeeded":
            return "Payment not successful"

        process_flight_booking_logic(payment)

        return "Flight booked successfully"

    except Exception as e:
        # Refund on failure
        if payment.flutterwave_charge_id:
            FlutterwaveService().refund_payment(payment.flutterwave_charge_id)
        payment.status = "booking_failed"
        payment.save(update_fields=["status"])

        raise self.retry(exc=e, countdown=60)
