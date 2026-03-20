from django.utils.decorators import method_decorator
from rest_framework import status, viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.conf import settings
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from app.services.booking_engine import BookingEngine
from app.services.flutterwave import FlutterwaveService
from app.services.reference_generator import generate_booking_reference
from app.payments.models import Payment
from app.transactions.services import get_or_create_transaction
from .permissions import IsAdminUserType
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from app.services.helper_function import _convert_amount, _get_user_currency,_quantize_amount,_to_decimal
from django.db.models import F, Q
from .models import Trip
from .serializers import TripSerializer


class TripViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TripSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if getattr(user, "user_type", None) == "admin":
            return Trip.objects.all()

        # Only available trips
        return Trip.objects.filter(
            status="scheduled"
        ).annotate(
            available_seats=F("capacity") - F("booked_seats")
        ).filter(available_seats__gt=0)
    
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdminUserType


class AdminTripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated, IsAdminUserType]

    @action(detail=True, methods=["post"])
    def start_trip(self, request, pk=None):
        trip = self.get_object()
        trip.status = "en_route"
        trip.save()
        return Response({"status": "Trip started"})

    @action(detail=True, methods=["post"])
    def complete_trip(self, request, pk=None):
        trip = self.get_object()
        trip.status = "completed"
        trip.save()
        return Response({"status": "Trip completed"})

from rest_framework import status, viewsets
from rest_framework.response import Response
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from .models import TransportBooking
from .serializers import TransportBookingSerializer
from .services import create_trip_booking
from app.services.flutterwave import FlutterwaveService
from app.services.reference_generator import generate_booking_reference
from app.payments.models import Payment


class TransportBookingViewSet(viewsets.ModelViewSet):
    serializer_class = TransportBookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if getattr(user, "user_type", None) == "admin":
            return TransportBooking.objects.all()

        return TransportBooking.objects.filter(user=user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data

        trip_id = data.get("trip_id")
        passengers = int(data.get("passengers", 1))
        organization = data.get("organization")

        if not trip_id:
            return Response({"error": "trip_id is required"}, status=400)

        Trip.objects.select_for_update().get(id=trip_id)

        try:
            booking = create_trip_booking(
                user=request.user,
                trip_id=trip_id,
                passengers=passengers,
                organization=organization
            )
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        # Payment
        tx_ref = generate_booking_reference("pay")

        payment_response = FlutterwaveService().initiate_card_payment(
            amount=booking.passengers * booking.trip.price_per_seat,
            currency="NGN",
            customer_email=request.user.email,
            tx_ref=tx_ref,
            payment_options="card,banktransfer",
        )

        booking = BookingEngine.create_booking(
            user=request.user,
            service_type="Transport",
            reference_code = generate_booking_reference("TRP"),
            total_price=confirmed_price,
            currency=currency,
        )

        Payment.objects.create(
            booking=booking,  # or link to your central booking model
            tx_ref=tx_ref,
            amount=booking.passengers * 100,
            currency="NGN",
            payment_method="card",
            status="pending",
        )

        return Response(
            {
                "booking_id": booking.id,
                "payment_link": payment_response.get("data", {}).get("link"),
                "tx_ref": tx_ref,
            },
            status=status.HTTP_201_CREATED,
        )
    
class TripSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pickup = request.query_params.get("pickup")
        dropoff = request.query_params.get("dropoff")
        date = request.query_params.get("date")

        trips = Trip.objects.filter(status="scheduled")

        if pickup:
            trips = trips.filter(pickup_location__icontains=pickup)

        if dropoff:
            trips = trips.filter(dropoff_location__icontains=dropoff)

        if date:
            trips = trips.filter(departure_time__date=date)

        trips = trips.annotate(
            available_seats=F("capacity") - F("booked_seats")
        ).filter(available_seats__gt=0)

        serializer = TripSerializer(trips, many=True)
        return Response(serializer.data)
    
from .models import TripAssignment
from .serializers import TripAssignmentSerializer


class TripAssignmentViewSet(viewsets.ModelViewSet):
    queryset = TripAssignment.objects.all()
    serializer_class = TripAssignmentSerializer
    permission_classes = [IsAuthenticated, IsAdminUserType]