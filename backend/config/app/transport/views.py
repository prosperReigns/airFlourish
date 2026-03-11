from django.utils.decorators import method_decorator
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from app.services.booking_engine import BookingEngine
from .models import TransportService
from .serializers import TransportServiceSerializer
from .permissions import IsAdminUserType
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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
    permission_classes = [permissions.IsAuthenticated]

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
    permission_classes = [permissions.IsAuthenticated, IsAdminUserType]

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
                                      }
                                  ),
                                    responses={
                                        201: "Transport booking created successfully",
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
    permission_classes = [permissions.IsAuthenticated]

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

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Creates a new transport booking. This method handles the booking process for a transport service. It checks if the transport service is available, calculates the total price based on the number of passengers, creates a booking using the BookingEngine, and associates the booking with the transport service. The method also handles special requests and ensures that the booking process is atomic to prevent race conditions.
        Expected request data for creating a transport booking:
        {
            "transport_id": 1,
            "passengers": 2,
            "special_requests": "Need a child seat"
        }
        """
        data = request.data
        transport_id = data.get("transport_id")

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

        total_price = transport.price_per_passenger * passengers

        booking = BookingEngine.create_booking(
            user=request.user,
            service_type="transport",
            total_price=total_price,
            currency=transport.currency,
            external_service_id=transport.id,
        )

        transport.booking = booking
        transport.passengers = passengers
        transport.special_requests = data.get("special_requests", "")
        transport.save()

        serializer = self.get_serializer(transport)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
