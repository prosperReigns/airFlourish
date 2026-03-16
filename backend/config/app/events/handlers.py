def handle_event(event):

    if event.event_type == "payment_confirmed":

        handle_payment_confirmed(event.payload)

    if event.event_type == "reservation_expired":

        handle_reservation_expired(event.payload)

def handle_payment_confirmed(payload):

    reservation_id = payload["reservation_id"]

    # confirm reservation
    confirm_reservation(reservation_id)

    # create booking
    create_booking(reservation_id)

    # send notification
    send_booking_notification(payload["user_id"])