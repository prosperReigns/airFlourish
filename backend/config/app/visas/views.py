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
from drf_yasg import openapi

@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List visa applications.",
                                  manual_parameters={
                                 "destination_country": openapi.Parameter(
                                     'destination_country', openapi.IN_QUERY, description="Filter by destination country", type=openapi.TYPE_STRING
                                 ),
                                 "visa_type": openapi.Parameter(
                                     'visa_type', openapi.IN_QUERY, description="Filter by visa type", type=openapi.TYPE_STRING
                                 ),
                                 "status": openapi.Parameter(
                                     'status', openapi.IN_QUERY, description="Filter by visa application status", type=openapi.TYPE_STRING
                                 ),
                                 "flight_id": openapi.Parameter(
                                     'flight_id', openapi.IN_QUERY, description="Filter by associated flight booking ID", type=openapi.TYPE_INTEGER
                                 ),
                             }
    )
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a visa application by ID.",
                                  responses={
                                      200: VisaApplicationSerializer(),
                                      404: "Visa application not found"
                                  }
    )
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(operation_description="Create a visa application.",
                                  request_body=VisaApplicationSerializer,
                                  responses={
                                      201: VisaApplicationSerializer(),
                                      400: "Invalid input data"
                                  },
                                  manual_parameters={
                                     "flight_id": openapi.Parameter(
                                         'flight_id', openapi.IN_QUERY, description="Optional flight booking ID to link with this visa application", type=openapi.TYPE_INTEGER
                                     ),
                                     "visa_fee": openapi.Parameter(
                                         'visa_fee', openapi.IN_QUERY, description="The fee for the visa application", type=openapi.TYPE_NUMBER
                                     ),
                                     "currency": openapi.Parameter(
                                         'currency', openapi.IN_QUERY, description="Currency code for the visa fee (e.g. USD, NGN)", type=openapi.TYPE_STRING
                                     ),
                                     "visa_id": openapi.Parameter(
                                         'visa_id', openapi.IN_QUERY, description="External ID from visa service provider (if applicable)", type=openapi.TYPE_STRING
                                     ),
                                     "destination_country": openapi.Parameter(
                                         'destination_country', openapi.IN_QUERY, description="The country for which the visa is being applied", type=openapi.TYPE_STRING
                                     ),
                                     "visa_type": openapi.Parameter(
                                         'visa_type', openapi.IN_QUERY, description="Type of visa (e.g. tourist, business)", type=openapi.TYPE_STRING
                                     ),
                                     "appointment_date": openapi.Parameter(
                                         'appointment_date', openapi.IN_QUERY, description="Date of visa appointment", type=openapi.FORMAT_DATE
                                     ),
                                     "passport_scan": openapi.Parameter(
                                         'passport_scan', openapi.IN_QUERY, description="Base64-encoded scan of the passport", type=openapi.TYPE_STRING
                                     ),
                                     "photo": openapi.Parameter(
                                         'photo', openapi.IN_QUERY, description="Base64-encoded photo for the visa application", type=openapi.TYPE_STRING
                                     ),
                                     "supporting_docs": openapi.Parameter(
                                         'supporting_docs', openapi.IN_QUERY, description="Base64-encoded supporting documents for the visa application", type=openapi.TYPE_STRING
                                      ),
                                  }
    )
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(operation_description="Update a visa application.",
                                  request_body=VisaApplicationSerializer,
                                  responses={
                                      200: VisaApplicationSerializer(),
                                      400: "Invalid input data",
                                      404: "Visa application not found"
                                  },
                                  manual_parameters={
                                     "destination_country": openapi.Parameter(
                                         'destination_country', openapi.IN_QUERY, description="The country for which the visa is being applied", type=openapi.TYPE_STRING
                                     ),
                                     "visa_type": openapi.Parameter(
                                         'visa_type', openapi.IN_QUERY, description="Type of visa (e.g. tourist, business)", type=openapi.TYPE_STRING
                                     ),
                                     "appointment_date": openapi.Parameter(
                                         'appointment_date', openapi.IN_QUERY, description="Date of visa appointment", type=openapi.FORMAT_DATE
                                     ),
                                     "passport_scan": openapi.Parameter(
                                         'passport_scan', openapi.IN_QUERY, description="Base64-encoded scan of the passport", type=openapi.TYPE_STRING
                                     ),
                                     "photo": openapi.Parameter(
                                         'photo', openapi.IN_QUERY, description="Base64-encoded photo for the visa application", type=openapi.TYPE_STRING
                                     ),
                                     "supporting_docs": openapi.Parameter(
                                         'supporting_docs', openapi.IN_QUERY, description="Base64-encoded supporting documents for the visa application", type=openapi.TYPE_STRING
                                      ),
                                  }
    )
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(operation_description="Partially update a visa application.",
                                  request_body=VisaApplicationSerializer,
                                  responses={
                                      200: VisaApplicationSerializer(),
                                      400: "Invalid input data",
                                      404: "Visa application not found"
                                  },
                                  manual_parameters={
                                     "destination_country": openapi.Parameter(
                                         'destination_country', openapi.IN_QUERY, description="The country for which the visa is being applied", type=openapi.TYPE_STRING
                                     ),
                                     "visa_type": openapi.Parameter(
                                         'visa_type', openapi.IN_QUERY, description="Type of visa (e.g. tourist, business)", type=openapi.TYPE_STRING
                                     ),
                                     "appointment_date": openapi.Parameter(
                                         'appointment_date', openapi.IN_QUERY, description="Date of visa appointment", type=openapi.FORMAT_DATE
                                     ),
                                     "passport_scan": openapi.Parameter(
                                         'passport_scan', openapi.IN_QUERY, description="Base64-encoded scan of the passport", type=openapi.TYPE_STRING
                                     ),
                                     "photo": openapi.Parameter(
                                         'photo', openapi.IN_QUERY, description="Base64-encoded photo for the visa application", type=openapi.TYPE_STRING
                                     ),
                                     "supporting_docs": openapi.Parameter(
                                         'supporting_docs', openapi.IN_QUERY, description="Base64-encoded supporting documents for the visa application", type=openapi.TYPE_STRING
                                      ),
                                  }
    )
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Delete a visa application.",
                                  responses={
                                      204: "Visa application deleted successfully",
                                      404: "Visa application not found"
                                  }
    ),
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
    @swagger_auto_schema(operation_description="Verify visa documents (admin).",
                         responses={
            200: "Documents verified successfully",
            404: "Visa application not found"
        }
    )
    def verify_documents(self, request, pk=None):
        visa = self.get_object()
        visa.status = "verified"
        visa.save()
        return Response({"status": "documents verified"})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    @swagger_auto_schema(operation_description="Submit visa to embassy (admin).",
                         responses={
                            200: "Visa submitted to embassy successfully",
                            404: "Visa application not found"
                         },
                         manual_parameters={
                             "visa_id": openapi.Parameter(
                                 'visa_id', openapi.IN_QUERY, description="External ID from visa service provider (if applicable)", type=openapi.TYPE_STRING
                             ),
                                "destination_country": openapi.Parameter(
                                    'destination_country', openapi.IN_QUERY, description="The country for which the visa is being applied", type=openapi.TYPE_STRING
                                ),
                                "visa_type": openapi.Parameter(
                                    'visa_type', openapi.IN_QUERY, description="Type of visa (e.g. tourist, business)", type=openapi.TYPE_STRING
                                ),
                                "appointment_date": openapi.Parameter(
                                    'appointment_date', openapi.IN_QUERY, description="Date of visa appointment", type=openapi.FORMAT_DATE
                                ),
                                "passport_scan": openapi.Parameter(
                                    'passport_scan', openapi.IN_QUERY, description="Base64-encoded scan of the passport", type=openapi.TYPE_STRING
                                ),
                                "photo": openapi.Parameter(
                                    'photo', openapi.IN_QUERY, description="Base64-encoded photo for the visa application", type=openapi.TYPE_STRING
                                ),
                                "supporting_docs": openapi.Parameter(
                                    'supporting_docs', openapi.IN_QUERY, description="Base64-encoded supporting documents for the visa application", type=openapi.TYPE_STRING
                                 ),
                                 "visa_fee": openapi.Parameter(
                                     'visa_fee', openapi.IN_QUERY, description="The fee for the visa application", type=openapi.TYPE_NUMBER
                                  ),
                                 "currency": openapi.Parameter(
                                     'currency', openapi.IN_QUERY, description="Currency code for the visa fee (e.g. USD, NGN)", type=openapi.TYPE_STRING
                                  ),
                                 "additional_info": openapi.Parameter(
                                     'additional_info', openapi.IN_QUERY, description="Any additional information or instructions for the embassy", type=openapi.TYPE_STRING
                                  ),
                                "applicant_info": openapi.Parameter(
                                     'applicant_info', openapi.IN_QUERY, description="Additional applicant information (e.g. occupation, employer)", type=openapi.TYPE_STRING
                                  ),
                                 "travel_history": openapi.Parameter(
                                     'travel_history', openapi.IN_QUERY, description="Applicant's recent travel history", type=openapi.TYPE_STRING
                                  ),
                                 "interview_date": openapi.Parameter(
                                     'interview_date', openapi.IN_QUERY, description="Scheduled date for visa interview (if applicable)", type=openapi.FORMAT_DATE
                                  ),
                                 "interview_location": openapi.Parameter(
                                     'interview_location', openapi.IN_QUERY, description="Location of visa interview (if applicable)", type=openapi.TYPE_STRING
                                  ),
                                 "processing_time": openapi.Parameter(
                                     'processing_time', openapi.IN_QUERY, description="Estimated processing time for the visa application", type=openapi.TYPE_STRING
                                  ),
                                 "consular_office": openapi.Parameter(
                                     'consular_office', openapi.IN_QUERY, description="Consular office handling the visa application", type=openapi.TYPE_STRING
                                  ),
                                 "contact_info": openapi.Parameter(
                                     'contact_info', openapi.IN_QUERY, description="Contact information for the applicant during processing", type=openapi.TYPE_STRING
                                  ),
                                 "emergency_contact": openapi.Parameter(
                                     'emergency_contact', openapi.IN_QUERY, description="Emergency contact information for the applicant", type=openapi.TYPE_STRING
                                  ),
                                 "additional_documents": openapi.Parameter(
                                     'additional_documents', openapi.IN_QUERY, description="Any additional documents required by the embassy", type=openapi.TYPE_STRING
                                  ),
                                 "special_requests": openapi.Parameter(
                                     'special_requests', openapi.IN_QUERY, description="Any special requests or accommodations needed for the visa application", type=openapi.TYPE_STRING
                                  ),
                                "embassy_submission_details": openapi.Parameter(
                                     'embassy_submission_details', openapi.IN_QUERY, description="Details about the embassy submission process", type=openapi.TYPE_STRING
                                  ),
                                 "visa_tracking_number": openapi.Parameter(
                                     'visa_tracking_number', openapi.IN_QUERY, description="Tracking number for the visa application (if provided by embassy)", type=openapi.TYPE_STRING
                                  ),
                                 "visa_decision_date": openapi.Parameter(
                                     'visa_decision_date', openapi.IN_QUERY, description="Date when the visa decision is expected or received", type=openapi.FORMAT_DATE
                                  ),
                                 "visa_decision": openapi.Parameter(
                                     'visa_decision', openapi.IN_QUERY, description="Outcome of the visa application (e.g. approved, rejected)", type=openapi.TYPE_STRING
                                  ),
                                 "next_steps": openapi.Parameter(
                                     'next_steps', openapi.IN_QUERY, description="Next steps for the applicant after submission (e.g. wait for decision, attend interview)", type=openapi.TYPE_STRING
                                  ),
                                 "additional_notes": openapi.Parameter(
                                     'additional_notes', openapi.IN_QUERY, description="Any additional notes or comments from the admin submitting the visa application", type=openapi.TYPE_STRING
                                  ),
                                 "applicant_remarks": openapi.Parameter(
                                     'applicant_remarks', openapi.IN_QUERY, description="Any remarks or comments from the applicant regarding their visa application", type=openapi.TYPE_STRING
                                  ),
                                 "admin_remarks": openapi.Parameter(
                                     'admin_remarks', openapi.IN_QUERY, description="Any remarks or comments from the admin handling the visa application", type=openapi.TYPE_STRING
                                  ),
                                 "embassy_response": openapi.Parameter(
                                     'embassy_response', openapi.IN_QUERY, description="Response or feedback from the embassy regarding the visa application", type=openapi.TYPE_STRING
                                  ),
                                 "final_status": openapi.Parameter(
                                     'final_status', openapi.IN_QUERY, description="Final status of the visa application after embassy review", type=openapi.TYPE_STRING
                                  ),
                                 "rejection_reason": openapi.Parameter(
                                     'rejection_reason', openapi.IN_QUERY, description="Reason for rejection if the visa application was denied", type=openapi.TYPE_STRING
                                  ),
                                 "approval_conditions": openapi.Parameter(
                                     'approval_conditions', openapi.IN_QUERY, description="Any conditions attached to the approval of the visa application", type=openapi.TYPE_STRING
                                  ),
                                    "visa_validity_period": openapi.Parameter(
                                        'visa_validity_period', openapi.IN_QUERY, description="Validity period of the visa if approved", type=openapi.TYPE_STRING
                                    ), "visa_entry_type": openapi.Parameter(
                                        'visa_entry_type', openapi.IN_QUERY, description="Type of entry allowed by the visa (e.g. single, multiple)", type=openapi.TYPE_STRING
                                    ), "visa_duration": openapi.Parameter(
                                        'visa_duration', openapi.IN_QUERY, description="Duration of stay allowed by the visa", type=openapi.TYPE_STRING
                                    ), "visa_issuance_date": openapi.Parameter(
                                        'visa_issuance_date', openapi.IN_QUERY, description="Date when the visa was issued (if approved)", type=openapi.FORMAT_DATE
                                    ), "visa_expiry_date": openapi.Parameter(
                                        'visa_expiry_date', openapi.IN_QUERY, description="Date when the visa expires (if approved)", type=openapi.FORMAT_DATE
                                    ), "embassy_interview_outcome": openapi.Parameter(
                                        'embassy_interview_outcome', openapi.IN_QUERY, description="Outcome of any embassy interview related to the visa application", type=openapi.TYPE_STRING
                                    ), "consular_officer_notes": openapi.Parameter(
                                        'consular_officer_notes', openapi.IN_QUERY, description="Notes from the consular officer reviewing the visa application", type=openapi.TYPE_STRING
                                     ),
                                     "application_processing_stages": openapi.Parameter(
                                         'application_processing_stages', openapi.IN_QUERY, description="Current stage of the visa application processing (e.g. initial review, background check)", type=openapi.TYPE_STRING
                                      ),
                                     "estimated_decision_timeframe": openapi.Parameter(
                                         'estimated_decision_timeframe', openapi.IN_QUERY, description="Estimated timeframe for receiving a decision on the visa application", type=openapi.TYPE_STRING
                                      ),
                                     "applicant_follow_up_actions": openapi.Parameter(
                                         'applicant_follow_up_actions', openapi.IN_QUERY, description="Any follow-up actions required from the applicant after submission (e.g. provide additional documents)", type=openapi.TYPE_STRING
                                      ),
                                     "admin_follow_up_actions": openapi.Parameter(
                                         'admin_follow_up_actions', openapi.IN_QUERY, description="Any follow-up actions required from the admin handling the visa application (e.g. contact embassy for updates)", type=openapi.TYPE_STRING
                                      ),
                                     "embassy_follow_up_actions": openapi.Parameter(
                                         'embassy_follow_up_actions', openapi.IN_QUERY, description="Any follow-up actions required from the embassy after receiving the visa application (e.g. schedule interview)", type=openapi.TYPE_STRING
                                      ),
                                     "final_decision_notes": openapi.Parameter(
                                         'final_decision_notes', openapi.IN_QUERY, description="Any notes or comments regarding the final decision on the visa application", type=openapi.TYPE_STRING
                                      ),"post_decision_instructions": openapi.Parameter(
                                         'post_decision_instructions', openapi.IN_QUERY, description="Instructions for the applicant after the final decision on the visa application (e.g. how to collect visa, next steps if rejected)", type=openapi.TYPE_STRING
                                      ),"additional_comments": openapi.Parameter(
                                         'additional_comments', openapi.IN_QUERY, description="Any additional comments or information related to the visa application", type=openapi.TYPE_STRING
                                      ),"embassy_submission_notes": openapi.Parameter(
                                         'embassy_submission_notes', openapi.IN_QUERY, description="Any notes or comments related to the submission of the visa application to the embassy", type=openapi.TYPE_STRING
                                      ),"document_verification_notes": openapi.Parameter(
                                         'document_verification_notes', openapi.IN_QUERY, description="Any notes or comments related to the verification of the visa application documents", type=openapi.TYPE_STRING
                                      ),"admin_submission_notes": openapi.Parameter(
                                         'admin_submission_notes', openapi.IN_QUERY, description="Any notes or comments from the admin submitting the visa application", type=openapi.TYPE_STRING
                                      ),"applicant_submission_notes": openapi.Parameter(
                                         'applicant_submission_notes', openapi.IN_QUERY, description="Any notes or comments from the applicant regarding their visa application submission", type=openapi.TYPE_STRING
                                      ),"embassy_review_notes": openapi.Parameter(
                                         'embassy_review_notes', openapi.IN_QUERY, description="Any notes or comments from the embassy during their review of the visa application", type=openapi.TYPE_STRING
                                      ),"final_decision_comments": openapi.Parameter(
                                         'final_decision_comments', openapi.IN_QUERY, description="Any comments related to the final decision on the visa application", type=openapi.TYPE_STRING
                                      ),"rejection_comments": openapi.Parameter(
                                         'rejection_comments', openapi.IN_QUERY, description="Any comments related to the rejection of the visa application (if applicable)", type=openapi.TYPE_STRING
                                      ),"approval_comments": openapi.Parameter(
                                         'approval_comments', openapi.IN_QUERY, description="Any comments related to the approval of the visa application (if applicable)", type=openapi.TYPE_STRING
                                      ),"additional_documentation_comments": openapi.Parameter(
                                         'additional_documentation_comments', openapi.IN_QUERY, description="Any comments related to additional documentation required for the visa application", type=openapi.TYPE_STRING
                                      ),"processing_time_comments": openapi.Parameter(
                                         'processing_time_comments', openapi.IN_QUERY, description="Any comments related to the processing time for the visa application", type=openapi.TYPE_STRING
                                      ),"interview_comments": openapi.Parameter(
                                         'interview_comments', openapi.IN_QUERY, description="Any comments related to a visa interview (if applicable)", type=openapi.TYPE_STRING
                                      ),"follow_up_comments": openapi.Parameter(
                                         'follow_up_comments', openapi.IN_QUERY, description="Any comments related to follow-up actions for the visa application", type=openapi.TYPE_STRING
                                      ),"final_status_comments": openapi.Parameter(
                                         'final_status_comments', openapi.IN_QUERY, description="Any comments related to the final status of the visa application", type=openapi.TYPE_STRING
                                      ),"embassy_communication_comments": openapi.Parameter(
                                         'embassy_communication_comments', openapi.IN_QUERY, description="Any comments related to communication with the embassy regarding the visa application", type=openapi.TYPE_STRING
                                      ),"applicant_communication_comments": openapi.Parameter(
                                         'applicant_communication_comments', openapi.IN_QUERY, description="Any comments related to communication with the applicant regarding their visa application", type=openapi.TYPE_STRING
                                      ),"admin_communication_comments": openapi.Parameter(
                                         'admin_communication_comments', openapi.IN_QUERY, description="Any comments related to communication from the admin handling the visa application", type=openapi.TYPE_STRING
                                      ),"document_submission_comments": openapi.Parameter(
                                         'document_submission_comments', openapi.IN_QUERY, description="Any comments related to the submission of documents for the visa application", type=openapi.TYPE_STRING
                                      ),"verification_comments": openapi.Parameter(
                                         'verification_comments', openapi.IN_QUERY, description="Any comments related to the verification process for the visa application", type=openapi.TYPE_STRING
                                      ),"submission_to_embassy_comments": openapi.Parameter(
                                         'submission_to_embassy_comments', openapi.IN_QUERY, description="Any comments related to the submission of the visa application to the embassy", type=openapi.TYPE_STRING
                                      ),"approval_process_comments": openapi.Parameter(
                                         'approval_process_comments', openapi.IN_QUERY, description="Any comments related to the approval process for the visa application", type=openapi.TYPE_STRING
                                      ),"rejection_process_comments": openapi.Parameter(
                                         'rejection_process_comments', openapi.IN_QUERY, description="Any comments related to the rejection process for the visa application", type=openapi.TYPE_STRING
                                      ),"final_decision_process_comments": openapi.Parameter(
                                         'final_decision_process_comments', openapi.IN_QUERY, description="Any comments related to the final decision process for the visa application", type=openapi.TYPE_STRING
                                      ),"overall_process_comments": openapi.Parameter(
                                         'overall_process_comments', openapi.IN_QUERY, description="Any comments related to the overall process of handling the visa application", type=openapi.TYPE_STRING
                                      ),"additional_process_comments": openapi.Parameter(
                                         'additional_process_comments', openapi.IN_QUERY, description="Any additional comments related to the process of handling the visa application", type=openapi.TYPE_STRING
                                      ),"special_requests": openapi.Parameter(
                                         'special_requests', openapi.IN_QUERY, description="Any special requests or accommodations needed for the visa application", type=openapi.TYPE_STRING
                                      ),"additional_info": openapi.Parameter(
                                         'additional_info', openapi.IN_QUERY, description="Any additional information or instructions for the embassy", type=openapi.TYPE_STRING
                                      ),"applicant_info": openapi.Parameter(
                                         'applicant_info', openapi.IN_QUERY, description="Additional applicant information (e.g. occupation, employer)", type=openapi.TYPE_STRING
                                      ),"travel_history": openapi.Parameter(
                                         'travel_history', openapi.IN_QUERY, description="Applicant's recent travel history", type=openapi.TYPE_STRING
                                      ),
                                    }
    )
    def submit_to_embassy(self, request, pk=None):
        visa = self.get_object()
        visa.document_status = "submitted"
        visa.save()
        return Response({"status": "submitted to embassy"})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    @swagger_auto_schema(operation_description="Approve a visa application (admin).",
                         responses={
                            200: "Visa application approved successfully",
                            404: "Visa application not found"
                         },
                         manual_parameters={
                             "visa_id": openapi.Parameter(
                                 'visa_id', openapi.IN_QUERY, description="External ID from visa service provider (if applicable)", type=openapi.TYPE_STRING
                             ),
                                "destination_country": openapi.Parameter(
                                    'destination_country', openapi.IN_QUERY, description="The country for which the visa is being applied", type=openapi.TYPE_STRING
                                ),
                                "visa_type": openapi.Parameter(
                                    'visa_type', openapi.IN_QUERY, description="Type of visa (e.g. tourist, business)", type=openapi.TYPE_STRING
                                ),
                                "appointment_date": openapi.Parameter(
                                    'appointment_date', openapi.IN_QUERY, description="Date of visa appointment", type=openapi.FORMAT_DATE
                                ),
                                "passport_scan": openapi.Parameter(
                                    'passport_scan', openapi.IN_QUERY, description="Base64-encoded scan of the passport", type=openapi.TYPE_STRING
                                ),
                                "photo": openapi.Parameter(
                                    'photo', openapi.IN_QUERY, description="Base64-encoded photo for the visa application", type=openapi.TYPE_STRING
                                ),
                                "supporting_docs": openapi.Parameter(
                                    'supporting_docs', openapi.IN_QUERY, description="Base64-encoded supporting documents for the visa application", type=openapi.TYPE_STRING
                                 ),
                                 "visa_fee": openapi.Parameter(
                                     'visa_fee', openapi.IN_QUERY, description="The fee for the visa application", type=openapi.TYPE_NUMBER
                                  ),
                                 "currency": openapi.Parameter(
                                     'currency', openapi.IN_QUERY, description="Currency code for the visa fee (e.g. USD, NGN)", type=openapi.TYPE_STRING
                                  ),
                                 "additional_info": openapi.Parameter(
                                     'additional_info', openapi.IN_QUERY, description="Any additional information or instructions for the embassy", type=openapi.TYPE_STRING
                                  ),
                                 "applicant_info": openapi.Parameter(
                                     'applicant_info', openapi.IN_QUERY, description="Additional applicant information (e.g. occupation, employer)", type=openapi.TYPE_STRING
                                  ),
                                 "travel_history": openapi.Parameter(
                                     'travel_history', openapi.IN_QUERY, description="Applicant's recent travel history", type=openapi.TYPE_STRING
                                  ),
                                 "interview_date": openapi.Parameter(
                                     'interview_date', openapi.IN_QUERY, description="Scheduled date for visa interview (if applicable)", type=openapi.FORMAT_DATE
                                  ),
                                    "interview_location": openapi.Parameter(
                                        'interview_location', openapi.IN_QUERY, description="Location of visa interview (if applicable)", type=openapi.TYPE_STRING
                                    ), "processing_time": openapi.Parameter(
                                        'processing_time', openapi.IN_QUERY, description="Estimated processing time for the visa application", type=openapi.TYPE_STRING
                                    ), "consular_office": openapi.Parameter(
                                        'consular_office', openapi.IN_QUERY, description="Consular office handling the visa application", type=openapi.TYPE_STRING
                                    ), "contact_info": openapi.Parameter(
                                        'contact_info', openapi.IN_QUERY, description="Contact information for the applicant during processing", type=openapi.TYPE_STRING
                                    ), "emergency_contact": openapi.Parameter(
                                        'emergency_contact', openapi.IN_QUERY, description="Emergency contact information for the applicant", type=openapi.TYPE_STRING
                                    ), "additional_documents": openapi.Parameter(
                                        'additional_documents', openapi.IN_QUERY, description="Any additional documents required by the embassy", type=openapi.TYPE_STRING
                                     ), "special_requests": openapi.Parameter(
                                         'special_requests', openapi.IN_QUERY, description="Any special requests or accommodations needed for the visa application", type=openapi.TYPE_STRING
                                      ),"embassy_submission_details": openapi.Parameter(
                                         'embassy_submission_details', openapi.IN_QUERY, description="Details about the embassy submission process", type=openapi.TYPE_STRING
                                      ), "visa_tracking_number": openapi.Parameter(
                                         'visa_tracking_number', openapi.IN_QUERY, description="Tracking number for the visa application (if provided by embassy)", type=openapi.TYPE_STRING
                                      ), "visa_decision_date": openapi.Parameter(
                                         'visa_decision_date', openapi.IN_QUERY, description="Date when the visa decision is expected or received", type=openapi.FORMAT_DATE
                                      ), "visa_decision": openapi.Parameter(
                                         'visa_decision', openapi.IN_QUERY, description="Outcome of the visa application (e.g. approved, rejected)", type=openapi.TYPE_STRING
                                      ), "next_steps": openapi.Parameter(
                                         'next_steps', openapi.IN_QUERY, description="Next steps for the applicant after submission (e.g. wait for decision, attend interview)", type=openapi.TYPE_STRING
                                      ), "additional_notes": openapi.Parameter(
                                         'additional_notes', openapi.IN_QUERY, description="Any additional notes or comments from the admin submitting the visa application", type=openapi.TYPE_STRING
                                      ), "applicant_remarks": openapi.Parameter(
                                         'applicant_remarks', openapi.IN_QUERY, description="Any remarks or comments from the applicant regarding their visa application", type=openapi.TYPE_STRING
                                      ), "admin_remarks": openapi.Parameter(
                                         'admin_remarks', openapi.IN_QUERY, description="Any remarks or comments from the admin handling the visa application", type=openapi.TYPE_STRING
                                      ), "embassy_response": openapi.Parameter(
                                         'embassy_response', openapi.IN_QUERY, description="Response or feedback from the embassy regarding the visa application", type=openapi.TYPE_STRING
                                      ), "final_status": openapi.Parameter(
                                         'final_status', openapi.IN_QUERY, description="Final status of the visa application after embassy review", type=openapi.TYPE_STRING
                                      ), "rejection_reason": openapi.Parameter(
                                         'rejection_reason', openapi.IN_QUERY, description="Reason for rejection if the visa application was denied", type=openapi.TYPE_STRING
                                      ), "approval_conditions": openapi.Parameter(
                                         'approval_conditions', openapi.IN_QUERY, description="Any conditions attached to the approval of the visa application", type=openapi.TYPE_STRING
                                      ), "visa_validity_period": openapi.Parameter(
                                         'visa_validity_period', openapi.IN_QUERY, description="Validity period of the visa if approved", type=openapi.TYPE_STRING
                                      ), "visa_entry_type": openapi.Parameter(
                                         'visa_entry_type', openapi.IN_QUERY, description="Type of entry allowed by the visa (e.g. single, multiple)", type=openapi.TYPE_STRING
                                      ), "visa_duration": openapi.Parameter(
                                         'visa_duration', openapi.IN_QUERY, description="Duration of stay allowed by the visa", type=openapi.TYPE_STRING
                                      ), "visa_issuance_date": openapi.Parameter(
                                         'visa_issuance_date', openapi.IN_QUERY, description="Date when the visa was issued (if approved)", type=openapi.FORMAT_DATE
                                      ), "visa_expiry_date": openapi.Parameter(
                                         'visa_expiry_date', openapi.IN_QUERY, description="Date when the visa expires (if approved)", type=openapi.FORMAT_DATE
                                      ), "embassy_interview_outcome": openapi.Parameter(
                                         'embassy_interview_outcome', openapi.IN_QUERY, description="Outcome of any embassy interview related to the visa application", type=openapi.TYPE_STRING
                                      ), "consular_officer_notes": openapi.Parameter(
                                         'consular_officer_notes', openapi.IN_QUERY, description="Notes from the consular officer reviewing the visa application", type=openapi.TYPE_STRING
                                      ), "application_processing_stages": openapi.Parameter(
                                         'application_processing_stages', openapi.IN_QUERY, description="Current stage of the visa application processing (e.g. initial review, background check)", type=openapi.TYPE_STRING
                                      ), "estimated_decision_timeframe": openapi.Parameter(
                                         'estimated_decision_timeframe', openapi.IN_QUERY, description="Estimated timeframe for receiving a decision on the visa application", type=openapi.TYPE_STRING
                                      ), "applicant_follow_up_actions": openapi.Parameter(
                                         'applicant_follow_up_actions', openapi.IN_QUERY, description="Any follow-up actions required from the applicant after submission (e.g. provide additional documents)", type=openapi.TYPE_STRING
                                      ), "admin_follow_up_actions": openapi.Parameter(
                                         'admin_follow_up_actions', openapi.IN_QUERY, description="Any follow-up actions required from the admin handling the visa application (e.g. contact embassy for updates)", type=openapi.TYPE_STRING
                                      ), "embassy_follow_up_actions": openapi.Parameter(
                                         'embassy_follow_up_actions', openapi.IN_QUERY, description="Any follow-up actions required from the embassy after receiving the visa application (e.g. schedule interview)", type=openapi.TYPE_STRING
                                      ), "final_decision_notes": openapi.Parameter(
                                         'final_decision_notes', openapi.IN_QUERY, description="Any notes or comments regarding the final decision on the visa application", type=openapi.TYPE_STRING
                                      ), "post_decision_instructions": openapi.Parameter(
                                         'post_decision_instructions', openapi.IN_QUERY, description="Instructions for the applicant after the final decision on the visa application (e.g. how to collect visa, next steps if rejected)", type=openapi.TYPE_STRING
                                      ), "additional_comments": openapi.Parameter(
                                         'additional_comments', openapi.IN_QUERY, description="Any additional comments or information related to the visa application", type=openapi.TYPE_STRING
                                      ), "embassy_submission_notes": openapi.Parameter(
                                         'embassy_submission_notes', openapi.IN_QUERY, description="Any notes or comments related to the submission of the visa application to the embassy", type=openapi.TYPE_STRING
                                      ), "document_verification_notes": openapi.Parameter(
                                         'document_verification_notes', openapi.IN_QUERY, description="Any notes or comments related to the verification of the visa application documents", type=openapi.TYPE_STRING
                                      ), "admin_submission_notes": openapi.Parameter(
                                         'admin_submission_notes', openapi.IN_QUERY, description="Any notes or comments from the admin submitting the visa application", type=openapi.TYPE_STRING
                                      ), "applicant_submission_notes": openapi.Parameter(
                                         'applicant_submission_notes', openapi.IN_QUERY, description="Any notes or comments from the applicant regarding their visa application submission", type=openapi.TYPE_STRING
                                      ), "embassy_review_notes": openapi.Parameter(
                                         'embassy_review_notes', openapi.IN_QUERY, description="Any notes or comments from the embassy during their review of the visa application", type=openapi.TYPE_STRING
                                      ), "final_decision_comments": openapi.Parameter(
                                         'final_decision_comments', openapi.IN_QUERY, description="Any comments related to the final decision on the visa application", type=openapi.TYPE_STRING
                                      ), "rejection_comments": openapi.Parameter(
                                         'rejection_comments', openapi.IN_QUERY, description="Any comments related to the rejection of the visa application (if applicable)", type=openapi.TYPE_STRING
                                      ), "approval_comments": openapi.Parameter(
                                         'approval_comments', openapi.IN_QUERY, description="Any comments related to the approval of the visa application (if applicable)", type=openapi.TYPE_STRING
                                      ), "additional_documentation_comments": openapi.Parameter(
                                         'additional_documentation_comments', openapi.IN_QUERY, description="Any comments related to additional documentation required for the visa application", type=openapi.TYPE_STRING
                                      ), "processing_time_comments": openapi.Parameter(
                                         'processing_time_comments', openapi.IN_QUERY, description="Any comments related to the processing time for the visa application", type=openapi.TYPE_STRING
                                      ), "interview_comments": openapi.Parameter(
                                         'interview_comments', openapi.IN_QUERY, description="Any comments related to a visa interview (if applicable)", type=openapi.TYPE_STRING
                                      ), "follow_up_comments": openapi.Parameter(
                                         'follow_up_comments', openapi.IN_QUERY, description="Any comments related to follow-up actions for the visa application", type=openapi.TYPE_STRING
                                      ), "final_status_comments": openapi.Parameter(
                                         'final_status_comments', openapi.IN_QUERY, description="Any comments related to the final status of the visa application", type=openapi.TYPE_STRING
                                      ), "embassy_communication_comments": openapi.Parameter(
                                         'embassy_communication_comments', openapi.IN_QUERY, description="Any comments related to communication with the embassy regarding the visa application", type=openapi.TYPE_STRING
                                      ), "applicant_communication_comments": openapi.Parameter(
                                         'applicant_communication_comments', openapi.IN_QUERY, description="Any comments related to communication with the applicant regarding their visa application", type=openapi.TYPE_STRING
                                      ), "admin_communication_comments": openapi.Parameter(
                                         'admin_communication_comments', openapi.IN_QUERY, description="Any comments related to communication from the admin handling the visa application", type=openapi.TYPE_STRING
                                      ), "document_submission_comments": openapi.Parameter(
                                         'document_submission_comments', openapi.IN_QUERY, description="Any comments related to the submission of documents for the visa application", type=openapi.TYPE_STRING
                                      ), "verification_comments": openapi.Parameter(
                                         'verification_comments', openapi.IN_QUERY, description="Any comments related to the verification process for the visa application", type=openapi.TYPE_STRING
                                      ), "submission_to_embassy_comments": openapi.Parameter(
                                         'submission_to_embassy_comments', openapi.IN_QUERY, description="Any comments related to the submission of the visa application to the embassy", type=openapi.TYPE_STRING
                                      ), "approval_process_comments": openapi.Parameter(
                                         'approval_process_comments', openapi.IN_QUERY, description="Any comments related to the approval process for the visa application", type=openapi.TYPE_STRING
                                      ), "rejection_process_comments": openapi.Parameter(
                                         'rejection_process_comments', openapi.IN_QUERY, description="Any comments related to the rejection process for the visa application", type=openapi.TYPE_STRING
                                      ), "final_decision_process_comments": openapi.Parameter(
                                         'final_decision_process_comments', openapi.IN_QUERY, description="Any comments related to the final decision process for the visa application", type=openapi.TYPE_STRING
                                      ), "overall_process_comments": openapi.Parameter(
                                         'overall_process_comments', openapi.IN_QUERY, description="Any comments related to the overall process of handling the visa application", type=openapi.TYPE_STRING
                                      ), "additional_process_comments": openapi.Parameter(
                                         'additional_process_comments', openapi.IN_QUERY, description="Any additional comments related to the process of handling the visa application", type=openapi.TYPE_STRING
                                      ), "special_requests": openapi.Parameter(
                                         'special_requests', openapi.IN_QUERY, description="Any special requests or accommodations needed for the visa application", type=openapi.TYPE_STRING
                                      ), "additional_info": openapi.Parameter(
                                         'additional_info', openapi.IN_QUERY, description="Any additional information or instructions for the embassy", type=openapi.TYPE_STRING
                                      ), "applicant_info": openapi.Parameter(
                                         'applicant_info', openapi.IN_QUERY, description="Additional applicant information (e.g. occupation, employer)", type=openapi.TYPE_STRING
                                      ), "travel_history": openapi.Parameter(
                                         'travel_history', openapi.IN_QUERY, description="Applicant's recent travel history", type=openapi.TYPE_STRING
                                      ),
                         }
    )
    def approve(self, request, pk=None):
        visa = self.get_object()
        visa.document_status = "approved"
        visa.save()
        return Response({"status": "approved"})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    @swagger_auto_schema(operation_description="Reject a visa application (admin).",
                         responses={
                            200: "Visa application rejected successfully",
                            404: "Visa application not found"
                            },
                            manual_parameters={
                             "rejection_reason": openapi.Parameter(
                                 'rejection_reason', openapi.IN_QUERY, description="Reason for rejecting the visa application", type=openapi.TYPE_STRING
                              ), "additional_comments": openapi.Parameter(
                                  'additional_comments', openapi.IN_QUERY, description="Any additional comments related to the rejection of the visa application", type=openapi.TYPE_STRING
                               ), "applicant_info": openapi.Parameter(
                                  'applicant_info', openapi.IN_QUERY, description="Additional applicant information (e.g. occupation, employer)", type=openapi.TYPE_STRING
                               ), "destination_country": openapi.Parameter(
                                  'destination_country', openapi.IN_QUERY, description="The country for which the visa was being applied", type=openapi.TYPE_STRING
                               ), "visa_type": openapi.Parameter(
                                  'visa_type', openapi.IN_QUERY, description="Type of visa that was being applied for (e.g. tourist, business)", type=openapi.TYPE_STRING
                               ), "travel_history": openapi.Parameter(
                                  'travel_history', openapi.IN_QUERY, description="Applicant's recent travel history", type=openapi.TYPE_STRING
                               ), "special_requests": openapi.Parameter(
                                  'special_requests', openapi.IN_QUERY, description="Any special requests or accommodations that were needed for the visa application", type=openapi.TYPE_STRING
                               ), "additional_info": openapi.Parameter(
                                  'additional_info', openapi.IN_QUERY, description="Any additional information or instructions that were provided to the embassy during the visa application process", type=openapi.TYPE_STRING
                               ), "document_verification_notes": openapi.Parameter(
                                         'document_verification_notes', openapi.IN_QUERY, description="Any notes or comments related to the verification of the visa application documents", type=openapi.TYPE_STRING
                                      ), "embassy_submission_notes": openapi.Parameter(
                                         'embassy_submission_notes', openapi.IN_QUERY, description="Any notes or comments related to the submission of the visa application to the embassy", type=openapi.TYPE_STRING
                                      ), "admin_submission_notes": openapi.Parameter(
                                         'admin_submission_notes', openapi.IN_QUERY, description="Any notes or comments from the admin submitting the visa application", type=openapi.TYPE_STRING
                                      ), "applicant_submission_notes": openapi.Parameter(
                                         'applicant_submission_notes', openapi.IN_QUERY, description="Any notes or comments from the applicant regarding their visa application submission", type=openapi.TYPE_STRING
                                      ), "embassy_review_notes": openapi.Parameter(
                                         'embassy_review_notes', openapi.IN_QUERY, description="Any notes or comments from the embassy during their review of the visa application", type=openapi.TYPE_STRING
                                      ), "final_decision_comments": openapi.Parameter(
                                         'final_decision_comments', openapi.IN_QUERY, description="Any comments related to the final decision on the visa application", type=openapi.TYPE_STRING
                                      ), "rejection_comments": openapi.Parameter(
                                         'rejection_comments', openapi.IN_QUERY, description="Any comments related to the rejection of the visa application", type=openapi.TYPE_STRING
                                      ), "approval_comments": openapi.Parameter(
                                         'approval_comments', openapi.IN_QUERY, description="Any comments related to the approval of the visa application (if applicable)", type=openapi.TYPE_STRING
                                      ), "additional_documentation_comments": openapi.Parameter(
                                         'additional_documentation_comments', openapi.IN_QUERY, description="Any comments related to additional documentation required for the visa application", type=openapi.TYPE_STRING
                                      )
                            }
    )
    def reject(self, request, pk=None):
        visa = self.get_object()
        visa.document_status = "rejected"
        visa.save()
        return Response({"status": "rejected"})
    
class VisaApprovalView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_description="Approve or reject a visa application (admin).",
                         responses={
                            200: "Visa application processed successfully",
                            400: "Invalid action specified",
                            403: "Only admins can approve/reject visas",
                            404: "Visa application not found"
                            },
                            manual_parameters={
                             "action": openapi.Parameter(
                                 'action', openapi.IN_QUERY, description="Action to perform on the visa application (approve or reject)", type=openapi.TYPE_STRING
                              ), "visa_id": openapi.Parameter(
                                 'visa_id', openapi.IN_QUERY, description="External ID from visa service provider (if applicable)", type=openapi.TYPE_STRING
                              ), "destination_country": openapi.Parameter(
                                  'destination_country', openapi.IN_QUERY, description="The country for which the visa was being applied", type=openapi.TYPE_STRING
                               ), "visa_type": openapi.Parameter(
                                  'visa_type', openapi.IN_QUERY, description="Type of visa that was being applied for (e.g. tourist, business)", type=openapi.TYPE_STRING
                               ), "travel_history": openapi.Parameter(
                                  'travel_history', openapi.IN_QUERY, description="Applicant's recent travel history", type=openapi.TYPE_STRING
                               ), "special_requests": openapi.Parameter(
                                  'special_requests', openapi.IN_QUERY, description="Any special requests or accommodations that were needed for the visa application", type=openapi.TYPE_STRING
                               ), "additional_info": openapi.Parameter(
                                  'additional_info', openapi.IN_QUERY, description="Any additional information or instructions that were provided to the embassy during the visa application process", type=openapi.TYPE_STRING
                               ), "rejection_reason": openapi.Parameter(
                                  'rejection_reason', openapi.IN_QUERY, description="Reason for rejecting the visa application (if applicable)", type=openapi.TYPE_STRING
                               ), "approval_conditions": openapi.Parameter(
                                  'approval_conditions', openapi.IN_QUERY, description="Any conditions attached to the approval of the visa application (if applicable)", type=openapi.TYPE_STRING
                               ), "visa_validity_period": openapi.Parameter(
                                  'visa_validity_period', openapi.IN_QUERY, description="Validity period of the visa if approved", type=openapi.TYPE_STRING
                               ), "visa_entry_type": openapi.Parameter(
                                  'visa_entry_type', openapi.IN_QUERY, description="Type of entry allowed by the visa if approved (e.g. single, multiple)", type=openapi.TYPE_STRING
                               ), "visa_duration": openapi.Parameter(
                                  'visa_duration', openapi.IN_QUERY, description="Duration of stay allowed by the visa if approved", type=openapi.TYPE_STRING
                               ), "visa_issuance_date": openapi.Parameter(
                                  'visa_issuance_date', openapi.IN_QUERY, description="Date when the visa was issued (if approved)", type=openapi.FORMAT_DATE
                               ), "visa_expiry_date": openapi.Parameter(
                                  'visa_expiry_date', openapi.IN_QUERY, description="Date when the visa expires (if approved)", type=openapi.FORMAT_DATE
                               ), "interview_comments": openapi.Parameter(
                                         'interview_comments', openapi.IN_QUERY, description="Any comments related to a visa interview (if applicable)", type=openapi.TYPE_STRING
                                      ), "follow_up_comments": openapi.Parameter(
                                         'follow_up_comments', openapi.IN_QUERY, description="Any comments related to follow-up actions for the visa application", type=openapi.TYPE_STRING
                                      ), "final_status_comments": openapi.Parameter(
                                         'final_status_comments', openapi.IN_QUERY, description="Any comments related to the final status of the visa application", type=openapi.TYPE_STRING
                                      ), "embassy_communication_comments": openapi.Parameter(
                                         'embassy_communication_comments', openapi.IN_QUERY, description="Any comments related to communication with the embassy regarding the visa application", type=openapi.TYPE_STRING
                                      ), "applicant_communication_comments": openapi.Parameter(
                                         'applicant_communication_comments', openapi.IN_QUERY, description="Any comments related to communication with the applicant regarding their visa application", type=openapi.TYPE_STRING
                                      ), "admin_communication_comments": openapi.Parameter(
                                         'admin_communication_comments', openapi.IN_QUERY, description="Any comments related to communication from the admin handling the visa application", type=openapi.TYPE_STRING
                                      ), "document_submission_comments": openapi.Parameter(
                                         'document_submission_comments', openapi.IN_QUERY, description="Any comments related to the submission of documents for the visa application", type=openapi.TYPE_STRING
                                      ), "verification_comments": openapi.Parameter(
                                         'verification_comments', openapi.IN_QUERY, description="Any comments related to the verification process for the visa application", type=openapi.TYPE_STRING
                                      ), "submission_to_embassy_comments": openapi.Parameter(
                                         'submission_to_embassy_comments', openapi.IN_QUERY, description="Any comments related to the submission of the visa application to the embassy", type=openapi.TYPE_STRING
                                      ), "approval_process_comments": openapi.Parameter(
                                         'approval_process_comments', openapi.IN_QUERY, description="Any comments related to the approval process for the visa application", type=openapi.TYPE_STRING
                                      ), "rejection_process_comments": openapi.Parameter(
                                         'rejection_process_comments', openapi.IN_QUERY, description="Any comments related to the rejection process for the visa application", type=openapi.TYPE_STRING
                                      ), "final_decision_process_comments": openapi.Parameter(
                                         'final_decision_process_comments', openapi.IN_QUERY, description="Any comments related to the final decision process for the visa application", type=openapi.TYPE_STRING
                                      ), "overall_process_comments": openapi.Parameter(
                                         'overall_process_comments', openapi.IN_QUERY, description="Any comments related to the overall process of handling the visa application", type=openapi.TYPE_STRING
                                      ), "additional_process_comments": openapi.Parameter(
                                         'additional_process_comments', openapi.IN_QUERY, description="Any additional comments related to the process of handling the visa application", type=openapi.TYPE_STRING
                                      ), "destination_country": openapi.Parameter(
                                          'destination_country', openapi.IN_QUERY, description="The country for which the visa was being applied", type=openapi.TYPE_STRING
                                       ), "visa_type": openapi.Parameter(
                                          'visa_type', openapi.IN_QUERY, description="Type of visa that was being applied for (e.g. tourist, business)", type=openapi.TYPE_STRING
                                       ), "travel_history": openapi.Parameter(
                                          'travel_history', openapi.IN_QUERY, description="Applicant's recent travel history", type=openapi.TYPE_STRING
                                       ), "special_requests": openapi.Parameter(
                                          'special_requests', openapi.IN_QUERY, description="Any special requests or accommodations that were needed for the visa application", type=openapi.TYPE_STRING
                                       ), "additional_info": openapi.Parameter(
                                          'additional_info', openapi.IN_QUERY, description="Any additional information or instructions that were provided to the embassy during the visa application process", type=openapi.TYPE_STRING
                                       ), "applicant_info": openapi.Parameter(
                                          'applicant_info', openapi.IN_QUERY, description="Additional applicant information (e.g. occupation, employer)", type=openapi.TYPE_STRING
                                        )
                            }
    )
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
