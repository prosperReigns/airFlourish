from django.utils.decorators import method_decorator
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework import status
from .models import Booking
from .serializers import BookingSerializer
import uuid
from app.services.amadeus import AmadeusService
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from app.services.booking_engine import BookingEngine
from app.security.throttles import BookingThrottle, FlightSearchThrottle
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from app.core.pagination import DefaultPagination

class BookingViewSet(viewsets.ModelViewSet):
   
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    #/bookings/ - list and create bookings
    #/bookings/<booking_id>/ - retrieve, update, delete a booking
    def get_queryset(self):
        if getattr(self, False):
            return Booking.objects.none()
        user = self.request.user

        #admin sees all bookings
        if getattr(user, "user_type", None) == "admin":
            return Booking.objects.all()

        # Regular users only see their own bookings
        return Booking.objects.filter(user=user)

    #/booking/create/ - create a new booking
    def perform_create(self, serializer):
        # Generate unique reference code and assign user
        reference = str(uuid.uuid4()).replace("-", "")[:12].upper()
        serializer.save(user=self.request.user, reference_code=reference)

    #/bookings/<booking_id>/ - update booking status (only admin can update)
    def update(self, request, *args, **kwargs):
        if getattr(request.user, "user_type", None) != "admin":
            return Response(
                    {"detail": "Only admin can update booking status."},
                    status=status.HTTP_403_FORBIDDEN
                    )
            return super().update(request, *args, **kwargs)

#/booking/search-flights/ - search for flights using Amadeus API
#bookings/create/ - create a new booking with hotel and flight details
class BookingCreateView(APIView):
  
    permission_classes = [IsAuthenticated]
    throttle_classes = [BookingThrottle]

#bookings/search-flights/ - search for flights using Amadeus API
class FlightSearchView(APIView):
 
    def get(self, request):
        origin = request.query_params.get('origin')
        destination = request.query_params.get('destination')
        departure_date = request.query_params.get('departure_date')
        return_date = request.query_params.get('return_date')
        if not origin or not destination or not departure_date:
            return Response(
                {"error": "origin, destination and departure_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        flights = AmadeusService.search_flights(origin, destination, departure_date, return_date)
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(flights, request, view=self)
        if page is not None:
            return paginator.get_paginated_response(page)
        return Response(flights)

    throttle_classes = [FlightSearchThrottle]

#bookings/<booking_id>/cancel/ - cancel a booking
class CancelBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

        BookingEngine.cancel_booking(booking, reason=request.data.get("reason"))

        return Response({"message": "Booking cancelled successfully"})
