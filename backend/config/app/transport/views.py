from django.utils.decorators import method_decorator
from rest_framework import status, viewsets
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
from .models import TransportService, TransportReservation
from .serializers import TransportServiceSerializer, TransportReservationSerializer
from .permissions import IsAdminUserType
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from app.services.helper_function import _convert_amount, _get_user_currency,_quantize_amount,_to_decimal

@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List available transport options.",
                                  responses={
                                      200: openapi.Response(
                                          description="List of available transport services",
                                          schema=openapi.Schema(
                                              type=openapi.TYPE_ARRAY,
                                              items=openapi.Schema(
                                                  type=openapi.TYPE_OBJECT,
                                                  properties={
                                                      "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                      "booking": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
                                                      "transport_type": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "pickup_location": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "dropoff_location": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "pickup_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                                      "dropoff_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                                      "company": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "price_per_passenger": openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal'),
                                                      "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                      "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
                                                  }
                                              )
                                          )
                                      ),
                                  }
    )
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a transport option by ID.",
                                  responses={
                                      200: openapi.Response(
                                          description="Transport service retrieved successfully",
                                          schema=openapi.Schema(
                                              type=openapi.TYPE_OBJECT,
                                              properties={
                                                  "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "booking": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
                                                  "transport_type": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "pickup_location": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "dropoff_location": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "pickup_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                                  "dropoff_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                                  "company": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "price_per_passenger": openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal'),
                                                  "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
                                              }
                                          )
                                      ),
                                  }
    )
)
class TransportViewSet(viewsets.ReadOnlyModelViewSet):
    """Viewset for retrieving transport services."""
    serializer_class = TransportServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Admin users can see all transport services, while regular users can only see available transport services that are not yet booked. This method overrides the default queryset to filter the transport services based on the user's permissions.
        Expected URL for listing transport services: /transports/
        """
        if getattr(self, 'swagger_fake_view', False):
            return TransportService.objects.none()
        
        if getattr(self.request.user, "user_type", None) == "admin":
            return TransportService.objects.all()
        return TransportService.objects.filter(booking__isnull=True)

#/admin/transports/<int:pk>/
@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List transport services (admin).",
                                  responses={
                                      200: openapi.Response(
                                          description="List of transport services",
                                          schema=openapi.Schema(
                                              type=openapi.TYPE_ARRAY,
                                              items=openapi.Schema(
                                                  type=openapi.TYPE_OBJECT,
                                                  properties={
                                                      "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                      "booking": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
                                                      "transport_type": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "pickup_location": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "dropoff_location": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "pickup_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                                      "dropoff_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                                      "company": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "price_per_passenger": openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal'),
                                                      "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                      "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
                                                  }
                                              )
                                          )
                                      ),
                                    }
    )
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a transport service by ID (admin).",
                                  responses={
                                      200: openapi.Response(
                                          description="Transport service retrieved successfully",
                                          schema=openapi.Schema(
                                              type=openapi.TYPE_OBJECT,
                                              properties={
                                                  "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "booking": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
                                                  "transport_type": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "pickup_location": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "dropoff_location": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "pickup_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                                  "dropoff_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                                  "company": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "price_per_passenger": openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal'),
                                                  "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
                                              }
                                          )
                                      ),
                                    }
    )
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(operation_description="Create a transport service (admin).",
                                  request_body=TransportServiceSerializer,
                                  responses={
                                      201: "Transport service created successfully",
                                      400: "Invalid input data"
                                  }
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(operation_description="Update a transport service (admin).",
                                  request_body=TransportServiceSerializer,
                                  responses={
                                      200: "Transport service updated successfully",
                                      400: "Invalid input data"
                                  }
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(operation_description="Partially update a transport service (admin).",
                                  request_body=TransportServiceSerializer,
                                  responses={
                                      200: "Transport service partially updated successfully",
                                      400: "Invalid input data"
                                  }
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Delete a transport service (admin).",
                                  responses={
                                      204: "Transport service deleted successfully",
                                      404: "Transport service not found"
                                  }
    ),
)
class AdminTransportViewSet(viewsets.ModelViewSet):
    """Viewset for admin users to manage transport services. Admin users can create, update, and delete transport services, while regular users have read-only access to the transport services.
    Expected URL for admin transport management: /admin/transports/
    """
    queryset = TransportService.objects.all()
    serializer_class = TransportServiceSerializer
    permission_classes = [IsAuthenticated, IsAdminUserType]

#/transport-bookings/<int:pk>/
@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List transport bookings.",
                                  responses={
                                      200: openapi.Response(
                                          description="List of transport bookings",
                                          schema=openapi.Schema(
                                              type=openapi.TYPE_ARRAY,
                                              items=openapi.Schema(
                                                  type=openapi.TYPE_OBJECT,
                                                  properties={
                                                      "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                      "booking": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
                                                      "transport_type": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "pickup_location": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "dropoff_location": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "pickup_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                                      "dropoff_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                                      "company": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "price_per_passenger": openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal'),
                                                      "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                      "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                      "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
                                                  }
                                              )
                                          )
                                      ),
                                  }
    )
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a transport booking by ID.",
                                  responses={
                                      200: openapi.Response(
                                          description="Transport booking retrieved successfully",
                                          schema=openapi.Schema(
                                              type=openapi.TYPE_OBJECT,
                                              properties={
                                                  "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "booking": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
                                                  "transport_type": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "pickup_location": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "dropoff_location": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "pickup_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                                  "dropoff_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                                  "company": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "price_per_passenger": openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal'),
                                                  "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
                                              }
                                          )
                                      ),
                                  }
    )
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(operation_description="Create a transport booking.",
                                  request_body=openapi.Schema(
                                      type=openapi.TYPE_OBJECT,
                                      properties={
                                          "transport_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                          "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                                          "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
                                          "payment_method": openapi.Schema(
                                              type=openapi.TYPE_STRING,
                                              description="Optional: card or bank_transfer. Omit to show both on hosted page.",
                                          ),
                                      }
                                  ),
                                    responses={
                                        201: openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                "payment_link": openapi.Schema(type=openapi.TYPE_STRING),
                                                "tx_ref": openapi.Schema(type=openapi.TYPE_STRING),
                                                "booking_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                "transport_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                "payment_options": openapi.Schema(type=openapi.TYPE_STRING),
                                                "bank_transfer_available": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                            },
                                        ),
                                        400: "Invalid input data",
                                        404: "Transport not found"
                                    }
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(operation_description="Update a transport booking.",
                                  request_body=openapi.Schema(
                                      type=openapi.TYPE_OBJECT,
                                      properties={
                                          "transport_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                          "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                                          "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
                                      }
                                  ),
                                  responses={
                                      200: "Transport booking updated successfully",
                                      400: "Invalid input data",
                                      404: "Transport not found"
                                  }
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(operation_description="Partially update a transport booking.",
                                  request_body=openapi.Schema(
                                      type=openapi.TYPE_OBJECT,
                                      properties={
                                          "transport_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                          "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                                          "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
                                      }
                                  ),
                                  responses={
                                      200: "Transport booking partially updated successfully",
                                      400: "Invalid input data",
                                      404: "Transport not found"
                                  }
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Delete a transport booking.",
                                  responses={
                                      204: "Transport booking deleted successfully",
                                      404: "Transport not found"
                                  }
    ),
)
class TransportBookingViewSet(viewsets.ModelViewSet):
    """Viewset for managing transport bookings. Regular users can only see and manage their own transport bookings, while admin users can see and manage all transport bookings.
    Expected URL for creating a transport booking: /transport-bookings/
    Expected request data for creating a transport booking:
    {
        "transport_id": 1,
        "passengers": 2,
        "special_requests": "Need a child seat"
    }
    """
    queryset = TransportService.objects.all()
    serializer_class = TransportServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Admin users can see all transport bookings, while regular users can only see their own transport bookings. This method overrides the default queryset to filter the transport bookings based on the user's permissions.
        Expected URL for listing transport bookings: /transport-bookings/
        """
        if getattr(self, "swagger_fake_view", False):
            return TransportService.objects.none()
        user = self.request.user
        if not user or not user.is_authenticated:
            return TransportService.objects.none()
        if getattr(user, "user_type", None) == "admin":
            return TransportService.objects.all()
        return TransportService.objects.filter(booking__user=user)

    @swagger_auto_schema(
        operation_description="Create a transport booking.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["transport_id"],
            properties={
                "transport_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            201: TransportServiceSerializer,
            400: "Invalid request",
            404: "Transport not found"
        }
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Creates a new transport booking. This method handles the booking process for a transport service. It checks if the transport service is available, calculates the total price based on the number of passengers, creates a booking using the BookingEngine, and associates the booking with the transport service. The method also handles special requests and ensures that the booking process is atomic to prevent race conditions.
        Expected request data for creating a transport booking:
        {
            "transport_id": 1,
            "passengers": 2,
            "special_requests": "Need a child seat",
            "payment_method": "card" // optional: card or bank_transfer
        }
        """
        data = request.data
        transport_id = data.get("transport_id")
        payment_method = (data.get("payment_method") or "").lower().strip()

        if not transport_id:
            return Response({"error": "transport_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            transport = TransportService.objects.select_for_update().get(id=transport_id)
        except TransportService.DoesNotExist:
            return Response({"error": "Transport not found"}, status=status.HTTP_404_NOT_FOUND)

        if transport.booking is not None:
            return Response({"error": "Transport already booked"}, status=status.HTTP_400_BAD_REQUEST)

        passengers = int(data.get("passengers", 1))
        if passengers < 1:
            return Response({"error": "passengers must be at least 1"}, status=status.HTTP_400_BAD_REQUEST)

        if payment_method and payment_method not in {"card", "bank_transfer"}:
            return Response(
                {"error": "payment_method must be 'card' or 'bank_transfer'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_price = transport.price_per_passenger * passengers
        base_currency = transport.currency or "NGN"
        amount = _to_decimal(total_price)
        if not amount:
            return Response(
                {"error": "Unable to determine transport price"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_currency = _get_user_currency(request.user, base_currency)
        converted_amount = _convert_amount(amount, base_currency, target_currency)
        conversion_applied = True
        if converted_amount is None:
            converted_amount = amount
            target_currency = base_currency
            conversion_applied = False

        confirmed_price = _quantize_amount(converted_amount)

        supported_bank_currencies = set(
            getattr(settings, "BANK_TRANSFER_SUPPORTED_CURRENCIES", ["NGN"])
        )
        bank_transfer_available = target_currency in supported_bank_currencies

        payment_options = "card,banktransfer"
        if not bank_transfer_available:
            payment_options = "card"
        if payment_method == "card":
            payment_options = "card"
        elif payment_method == "bank_transfer":
            payment_options = "banktransfer" if bank_transfer_available else "card"

        tx_ref = generate_booking_reference("pay")
        payment_response = FlutterwaveService().initiate_card_payment(
            amount=confirmed_price,
            currency=target_currency,
            customer_email=request.user.email,
            tx_ref=tx_ref,
            payment_options=payment_options,
        )
        if payment_response.get("status") == "error":
            return Response(
                {"error": "Payment initiation failed", "details": payment_response.get("message")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking = BookingEngine.create_booking(
            user=request.user,
            service_type="transport",
            total_price=confirmed_price,
            currency=target_currency,
            external_service_id=transport.id,
        )

        transport.booking = booking
        transport.passengers = passengers
        transport.special_requests = data.get("special_requests", "")
        transport.save()

        meta = {
            "transport_id": transport.id,
            "transport_name": transport.transport_name,
            "passengers": passengers,
            "special_requests": transport.special_requests,
            "pickup_location": transport.pickup_location,
            "dropoff_location": transport.dropoff_location,
            "original_price": str(total_price),
            "original_currency": base_currency,
            "converted_price": str(confirmed_price),
            "converted_currency": target_currency,
            "conversion_applied": conversion_applied,
        }

        Payment.objects.create(
            booking=booking,
            tx_ref=tx_ref,
            amount=confirmed_price,
            currency=target_currency,
            payment_method=payment_method or "card",
            status="pending",
            raw_response={"meta": meta},
        )

        get_or_create_transaction(
            booking=booking,
            reference=tx_ref,
            amount=confirmed_price,
            currency=target_currency,
        )

        return Response(
            {
                "payment_link": payment_response.get("data", {}).get("link"),
                "tx_ref": tx_ref,
                "booking_id": booking.id,
                "transport_id": transport.id,
                "payment_options": payment_options,
                "bank_transfer_available": bank_transfer_available,
            },
            status=status.HTTP_201_CREATED,
        )

#/transport-search/
class TransportSearchView(APIView):
    """View for searching transport services based on pickup location, dropoff location, and vehicle type. Regular users can search for available transport services, while admin users can search through all transport services.
    Expected URL for searching transport services: /transport-search/
    Expected query parameters for searching transport services:
    - pickup: Search for transport services with a pickup location that contains the specified value (e.g., /transport-search/?pickup=Main+St)
    - dropoff: Search for transport services with a dropoff location that contains the specified value (e.g., /transport-search/?dropoff=Elm+St)
    - vehicle_type: Search for transport services with a specific vehicle type (e.g., /transport-search/?vehicle_type=car)
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_description="Search available transport options.",
                         manual_parameters=[
                             openapi.Parameter("pickup", openapi.IN_QUERY, description="Pickup location", type=openapi.TYPE_STRING),
                             openapi.Parameter("dropoff", openapi.IN_QUERY, description="Dropoff location", type=openapi.TYPE_STRING),
                             openapi.Parameter("vehicle_type", openapi.IN_QUERY, description="Vehicle type", type=openapi.TYPE_STRING)
                         ],
                         responses={
                             200: openapi.Response(
                                 description="List of transport services matching the search criteria",
                                 schema=openapi.Schema(
                                     type=openapi.TYPE_ARRAY,
                                     items=openapi.Schema(
                                         type=openapi.TYPE_OBJECT,
                                         properties={
                                             "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                             "booking": openapi.Schema(type=openapi.TYPE_OBJECT, nullable=True),
                                             "transport_type": openapi.Schema(type=openapi.TYPE_STRING),
                                             "pickup_location": openapi.Schema(type=openapi.TYPE_STRING),
                                             "dropoff_location": openapi.Schema(type=openapi.TYPE_STRING),
                                             "pickup_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                             "dropoff_time": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                             "company": openapi.Schema(type=openapi.TYPE_STRING),
                                             "price_per_passenger": openapi.Schema(type=openapi.TYPE_NUMBER, format='decimal'),
                                             "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                             "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                                             "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
                                         }
                                     )
                                 )
                             ),
                            }
    )
    def get(self, request):
        """Searches for transport services based on the provided query parameters. This method filters the transport services based on the pickup location, dropoff location, and vehicle type specified in the query parameters. Regular users can only search for available transport services that are not yet booked, while admin users can search through all transport services.
        Expected query parameters for searching transport services:
        - pickup: Search for transport services with a pickup location that contains the specified value (e.g., /transport-search/?pickup=Main+St)
        - dropoff: Search for transport services with a dropoff location that contains the specified value (e.g., /transport-search/?dropoff=Elm+St)
        - vehicle_type: Search for transport services with a specific vehicle type (e.g., /transport-search/?vehicle_type=car)
        Expected response data:
        [
            {
                "id": 1,
                "booking": null,
                "transport_type": "car",
                "pickup_location": "123 Main St, City",
                "dropoff_location": "456 Elm St, City",
                "pickup_time": "2023-10-01T10:00:00Z",
                "dropoff_time": "2023-10-01T12:00:00Z",
                "company": "Transport Co",
                "price_per_passenger": 25.00,
                "currency": "USD",
                "passengers": 0,
                "special_requests": ""
            },
            // more transport services...
        ]
        """
        pickup = request.query_params.get("pickup")
        dropoff = request.query_params.get("dropoff")
        vehicle_type = request.query_params.get("vehicle_type")

        transports = TransportService.objects.filter(booking__isnull=True)

        if pickup:
            transports = transports.filter(pickup_location__icontains=pickup)
        if dropoff:
            transports = transports.filter(dropoff_location__icontains=dropoff)
        if vehicle_type:
            transports = transports.filter(vehicle_type=vehicle_type)

        serializer = TransportServiceSerializer(transports, many=True)
        return Response(serializer.data)

@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_description="List all transport reservations (admin).",
        responses={200: TransportReservationSerializer(many=True)}
    ),
)
class TransportReservationViewSet(viewsets.ModelViewSet):
    """Viewset for managing transport reservations by regular users."""
    serializer_class = TransportReservationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Regular users can only see their own reservations."""
        user = self.request.user
        if getattr(user, "user_type", None) == "admin":
            return TransportReservation.objects.all()
        return TransportReservation.objects.filter(reserved_by=user)

    @swagger_auto_schema(
        operation_description="Create a reservation for a transport service.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["transport_id"],
            properties={
                "transport_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "passengers": openapi.Schema(type=openapi.TYPE_INTEGER),
                "special_requests": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            201: TransportReservationSerializer,
            404: "Transport service not found",
            400: "Transport already booked"
        }

    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Create a transport reservation for a service."""
        data = request.data
        transport_id = data.get("transport_id")
        passengers = int(data.get("passengers", 1))
        special_requests = data.get("special_requests", "")

        try:
            transport = TransportService.objects.select_for_update().get(id=transport_id)
        except TransportService.DoesNotExist:
            return Response({"error": "Transport service not found"}, status=status.HTTP_404_NOT_FOUND)

        if transport.booking is not None:
            return Response({"error": "Transport already booked"}, status=status.HTTP_400_BAD_REQUEST)

        reservation = TransportReservation.objects.create(
            service=transport,
            reserved_by=request.user,
            passengers_count=passengers,
            special_requests=special_requests
        )

        serializer = self.get_serializer(reservation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="Cancel a transport reservation.",
        responses={
            200: TransportReservationSerializer,
            404: "Reservation not found"
        }
    )
    @action(detail=True, methods=["post"], url_path="cancel", url_name="cancel")
    def cancel_reservation(self, request, pk=None):
        """Cancel a reservation. Only the user who reserved it or admin can cancel."""
        try:
            reservation = self.get_queryset().get(pk=pk)
        except TransportReservation.DoesNotExist:
            return Response({"error": "Reservation not found"}, status=status.HTTP_404_NOT_FOUND)

        reservation.status = "cancelled"
        reservation.save()
        serializer = self.get_serializer(reservation)
        return Response(serializer.data)
    
class AdminTransportReservationViewSet(viewsets.ModelViewSet):
    """Admin viewset to manage all transport reservations."""
    queryset = TransportReservation.objects.all()
    serializer_class = TransportReservationSerializer
    permission_classes = [IsAuthenticated, IsAdminUserType]
