from .models import Event


def publish_event(event_type, payload):

    Event.objects.create(
        event_type=event_type,
        payload=payload
    )