from django.test import TestCase
from django.utils import timezone

from app.events.models import Event


class EventModelTests(TestCase):
    def test_processed_defaults_false(self):
        event = Event.objects.create(event_type="booking", payload={"id": "evt-1"})
        self.assertFalse(event.processed)

    def test_processed_at_defaults_none(self):
        event = Event.objects.create(event_type="booking", payload={"id": "evt-2"})
        self.assertIsNone(event.processed_at)

    def test_payload_saved(self):
        payload = {"id": "evt-3", "status": "created"}
        event = Event.objects.create(event_type="booking", payload=payload)
        self.assertEqual(event.payload, payload)

    def test_mark_processed_sets_timestamp(self):
        event = Event.objects.create(event_type="booking", payload={"id": "evt-4"})
        event.processed = True
        event.processed_at = timezone.now()
        event.save()
        event.refresh_from_db()
        self.assertTrue(event.processed)
        self.assertIsNotNone(event.processed_at)
