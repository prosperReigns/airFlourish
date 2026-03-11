from tkinter.messagebox import IGNORE

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
from rest_framework.throttling import UserRateThrottle
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List bookings.",
                                  responses={
                                      200: BookingSerializer(many=True),
                                      403: "Forbidden"
                                  }
                                ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a booking by ID.",
                                  responses={
                                      200: BookingSerializer(),
                                      403: "Forbidden",
                                      404: "Booking not found"
                                  }
    ),
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(operation_description="Create a booking.",
                                  request_body=BookingSerializer,
                                  responses={
                                      201: BookingSerializer(),
                                      400: "Invalid input data",
                                      403: "Forbidden"
                                  }
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(operation_description="Update a booking (admin only).",
                                  request_body=BookingSerializer,
                                  responses={
                                      200: BookingSerializer(),
                                      400: "Invalid input data",
                                      403: "Forbidden",
                                      404: "Booking not found"
                                  }
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(operation_description="Partially update a booking (admin only).",
                                  request_body=BookingSerializer,
                                  responses={
                                      200: BookingSerializer(),
                                      400: "Invalid input data",
                                      403: "Forbidden",
                                      404: "Booking not found"
                                  }
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Delete a booking.",
                                  responses={
                                      204: "Booking deleted successfully",
                                      403: "Forbidden",
                                      404: "Booking not found"
                                  }
                                ),
)
class BookingViewSet(viewsets.ModelViewSet):
    """ViewSet for managing bookings. Regular users can only see and manage their own bookings, while admin users can see and manage all bookings.
    Expected URL for listing bookings: /bookings/
    Expected URL for retrieving a booking: /bookings/<booking_id>/
    Expected URL for creating a booking: /bookings/create/
    Expected URL for updating a booking: /bookings/<booking_id>/
    Expected URL for cancelling a booking: /bookings/<booking_id>/cancel/
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    #/bookings/ - list and create bookings
    #/bookings/<booking_id>/ - retrieve, update, delete a booking
    def get_queryset(self):
        """Admin users can see all bookings, regular users can only see their own bookings.
        Expected URL for listing bookings: /bookings/"""
        if getattr(self, 'swagger_fake_view', False):
            return Booking.objects.none()
        user = self.request.user

        #admin sees all bookings
        if getattr(user, "user_type", None) == "admin":
            return Booking.objects.all()

        # Regular users only see their own bookings
        return Booking.objects.filter(user=user)

    #/booking/create/ - create a new booking
    def perform_create(self, serializer):
        """Generates a unique reference code for the booking and assigns the authenticated user as the owner of the booking when creating a new booking instance.
        Expected request data for creating a booking:
        {
            "hotel_id": 1,
            "flight_id": 1,
            "check_in": "2023-10-01",
            "check_out": "2023-10-05",
            "guests": 2
        }
        """
        # Generate unique reference code and assign user
        reference = str(uuid.uuid4()).replace("-", "")[:12].upper()
        serializer.save(user=self.request.user, reference_code=reference)

    #/bookings/<booking_id>/ - update booking status (only admin can update)
    def update(self, request, *args, **kwargs):
        """Only admin users can update booking status. Regular users cannot update their bookings after creation.
        Expected URL: /bookings/<booking_id>/
        Expected request data for admin users:
        {
            "status": "confirmed"  // or "cancelled"
        }
        """
        if getattr(request.user, "user_type", None) != "admin":
            return Response(
                    {"detail": "Only admin can update booking status."},
                    status=status.HTTP_403_FORBIDDEN
                    )
            return super().update(request, *args, **kwargs)

#/booking/search-flights/ - search for flights using Amadeus API
class BookingThrottle(UserRateThrottle):
    """Custom throttle for booking creation to prevent abuse. This throttle limits booking creation to 10 per minute per user."""
    rate = "10/minute"

#bookings/create/ - create a new booking with hotel and flight details
class BookingCreateView(APIView):
    """Endpoint for creating a new booking. This endpoint allows authenticated users to create a new booking by providing the necessary details such as hotel, flight, and other relevant information.
    Expected URL: /bookings/create/
    Expected request data:
    {
        "hotel_id": 1,
        "flight_id": 1,
        "check_in": "2023-10-01",
        "check_out": "2023-10-05",
        "guests": 2
    }
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [BookingThrottle]

#bookings/search-flights/ - search for flights using Amadeus API
class FlightSearchView(APIView):
    """Endpoint for searching flights using the Amadeus API. This endpoint allows authenticated users to search for flights based on origin, destination, departure date, and optional return date.
    Expected URL: /bookings/search-flights/
    Expected query parameters:
    - origin: IATA code of the departure airport (required)
    - destination: IATA code of the arrival airport (required)
    - departure_date: Date of departure in YYYY-MM-DD format (required)
    - return_date: Date of return in YYYY-MM-DD format (optional)
    Example request: /bookings/search-flights/?origin=JFK&destination=LAX&departure_date=2023-10-01&return_date=2023-10-05
    """
    @swagger_auto_schema(operation_description="Search flights by origin, destination, and dates.",
                                  manual_parameters=[
                                         openapi.Parameter(
                                             'origin', openapi.IN_QUERY, description="IATA code of the departure airport", type=openapi.TYPE_STRING, required=True
                                         ),
                                         openapi.Parameter(
                                             'destination', openapi.IN_QUERY, description="IATA code of the arrival airport", type=openapi.TYPE_STRING, required=True
                                         ),
                                         openapi.Parameter(
                                             'departure_date', openapi.IN_QUERY, description="Date of departure in YYYY-MM-DD format", type=openapi.TYPE_STRING, required=True
                                         ),
                                         openapi.Parameter(
                                             'return_date', openapi.IN_QUERY, description="Date of return in YYYY-MM-DD format (optional)", type=openapi.TYPE_STRING, required=False
                                         ),
                                         openapi.Parameter(
                                             'limit', openapi.IN_QUERY, description="Maximum number of results to return", type=openapi.TYPE_INTEGER, required=False
                                         )
                                    ]
                                )
    def get(self, request):
        """Searches for flights using the Amadeus API based on the provided query parameters.
        Expected URL: /bookings/search-flights/
        Expected query parameters:
        - origin: IATA code of the departure airport (required)
        - destination: IATA code of the arrival airport (required)
        - departure_date: Date of departure in YYYY-MM-DD format (required)
        - return_date: Date of return in YYYY-MM-DD format (optional)
        Example request: /bookings/search-flights/?origin=JFK&destination=LAX&departure_date=2023-10-01&return_date=2023-10-05
        Expected response data:
        [
            {
                "flight_id": 1,
                "origin": "JFK",
                "destination": "LAX",
                "departure_date": "2023-10-01",
                "return_date": "2023-10-05"
            }
        ]
        """
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
        return Response(flights)

#bookings/<booking_id>/cancel/ - cancel a booking
class CancelBookingView(APIView):
    """"Endpoint for cancelling a booking. Only the user who made the booking or an admin can cancel it.
    Expected URL: /bookings/<booking_id>/cancel/
    Expected request data:
    {
        "reason": "Reason for cancellation (optional)"
    }
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_description="Cancel a booking by ID.",
                                  request_body=openapi.Schema(
                                      type=openapi.TYPE_OBJECT,
                                      properties={
                                          "reason": openapi.Schema(type=openapi.TYPE_STRING, description="Reason for cancellation (optional)")
                                      },
                                      required=[]
                                  ),
                                  responses={
                                      200: "Booking cancelled successfully",
                                      400: "Invalid booking ID or missing reason",
                                      403: "Forbidden",
                                      404: "Booking not found"
                                  }
    )
    def post(self, request, booking_id):
        """Cancels a booking by its ID. Only the user who made the booking or an admin can cancel it.
        Expected URL: /bookings/<booking_id>/cancel/
        Expected request data:
        {
            "reason": "Reason for cancellation (optional)"
        }
        """
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

        BookingEngine.cancel_booking(booking, reason=request.data.get("reason"))

        return Response({"message": "Booking cancelled successfully"})
