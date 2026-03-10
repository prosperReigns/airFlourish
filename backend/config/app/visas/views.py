# visas/views.py
from django.utils.decorators import method_decorator
from rest_framework import status, permissions, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import transaction
from app.services.booking_engine import BookingEngine
from .models import VisaApplication
from .serializers import VisaApplicationSerializer
from app.flights.models import FlightBooking
from app.payments.models import Payment
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema

@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List visa applications."),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a visa application by ID."),
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(operation_description="Create a visa application."),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(operation_description="Update a visa application."),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(operation_description="Partially update a visa application."),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Delete a visa application."),
)
class VisaApplicationViewSet(viewsets.ModelViewSet):
    queryset = VisaApplication.objects.all()
    serializer_class = VisaApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return VisaApplication.objects.none()
        user = self.request.user
        if getattr(user, "user_type", None) == "admin":
            return VisaApplication.objects.all()
        return VisaApplication.objects.filter(booking__user=user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user = request.user
        data = request.data

        flight_id = data.get("flight_id")
        flight = None
        if flight_id:
            try:
                flight = FlightBooking.objects.get(id=flight_id, booking__user=request.user)
            except FlightBooking.DoesNotExist:
                return Response({"error": "Flight booking not found for this user"}, status=status.HTTP_404_NOT_FOUND)

            # Step 1: Check if flight destination matches visa country
            visa_country = data.get("destination_country")
            if visa_country and flight.arrival_city.lower() != visa_country.lower():
                return Response(
                    {"error": "Flight destination does not match visa country"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Ensure flight is paid
            paid = Payment.objects.filter(booking=flight.booking, status="successful").exists()
            if not paid:
                return Response({"error": "Flight must be paid before visa application"}, status=status.HTTP_400_BAD_REQUEST)

            # Step 2: Check if a visa already exists for this flight
            existing_visa = VisaApplication.objects.filter(booking__user=user, flight=flight).first()
            if existing_visa:
                return Response(
                    {"error": "A visa application already exists for this flight"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Step 3: Create unified booking
        booking = BookingEngine.create_booking(
            user=request.user,
            service_type="visa",
            total_price=data.get("visa_fee"),
            currency=data.get("currency", "NGN"),
            external_service_id=data.get("visa_id", None)
        )

        # Step 4: Create VisaApplication linked to booking
        visa = VisaApplication.objects.create(
            booking=booking,
            flight=flight,
            destination_country=data.get("destination_country"),
            visa_type=data.get("visa_type"),
            appointment_date=data.get("appointment_date"),
            passport_scan=data.get("passport_scan"),
            photo=data.get("photo"),
            supporting_docs=data.get("supporting_docs")
        )

        serializer = self.get_serializer(visa)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # Admin actions
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    @swagger_auto_schema(operation_description="Verify visa documents (admin).")
    def verify_documents(self, request, pk=None):
        visa = self.get_object()
        visa.status = "verified"
        visa.save()
        return Response({"status": "documents verified"})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    @swagger_auto_schema(operation_description="Submit visa to embassy (admin).")
    def submit_to_embassy(self, request, pk=None):
        visa = self.get_object()
        visa.document_status = "submitted"
        visa.save()
        return Response({"status": "submitted to embassy"})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    @swagger_auto_schema(operation_description="Approve a visa application (admin).")
    def approve(self, request, pk=None):
        visa = self.get_object()
        visa.document_status = "approved"
        visa.save()
        return Response({"status": "approved"})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    @swagger_auto_schema(operation_description="Reject a visa application (admin).")
    def reject(self, request, pk=None):
        visa = self.get_object()
        visa.document_status = "rejected"
        visa.save()
        return Response({"status": "rejected"})
    
class VisaApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_description="Approve or reject a visa application (admin).")
    def post(self, request, visa_id):
        user = request.user
        action = request.data.get("action")  # "approve" or "reject"

        if getattr(user, "user_type", None) != "admin":
            return Response({"error": "Only admins can approve/reject visas"}, status=status.HTTP_403_FORBIDDEN)

        try:
            visa = VisaApplication.objects.get(id=visa_id)
        except VisaApplication.DoesNotExist:
            return Response({"error": "Visa application not found"}, status=status.HTTP_404_NOT_FOUND)

        if action == "approve":
            visa.status = "approved"
            visa.approved_at = timezone.now()
        elif action == "reject":
            visa.status = "rejected"
            visa.rejected_at = timezone.now()
        else:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        visa.reviewed_at = timezone.now()
        visa.save()

        return Response({"message": f"Visa {action}d successfully", "status": visa.status})
