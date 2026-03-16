from django.core.management.base import BaseCommand
from events.models import Event
from events.handlers import handle_event


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        events = Event.objects.filter(processed=False)

        for event in events:

            handle_event(event)

            event.processed = True
            event.save()