from django.db import models
from app.bookings.models import Booking


class Airport(models.Model):
    code = models.CharField(max_length=10, unique=True, db_index=True)
    city = models.CharField(max_length=100, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    country = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.city} ({self.code})"


class FlightBooking(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    departure_city = models.CharField(max_length=100)
    arrival_city = models.CharField(max_length=100)
    departure_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    airline = models.CharField(max_length=100)
    passengers = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.departure_city} to {self.arrival_city}"
