from datetime import datetime

from django.db import transaction
from django.utils.decorators import method_decorator
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from app.services.booking_engine import BookingEngine
from .models import Hotel, HotelReservation
from .permissions import IsAdminUserType
from .serializers import HotelReservationSerializer, HotelSerializer
from rest_framework.permissions import IsAuthenticated
from drf_yasg import openapi

@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List available hotels.",
                                  manual_parameters=[
                                 openapi.Parameter(
                                     'city', openapi.IN_QUERY, description="Filter hotels by city", type=openapi.TYPE_STRING
                                 ),
                                 openapi.Parameter(
                                     'check_in', openapi.IN_QUERY, description="Filter hotels available for check-in date (YYYY-MM-DD)", type=openapi.TYPE_STRING
                                 ),
                                 openapi.Parameter(
                                     'check_out', openapi.IN_QUERY, description="Filter hotels available for check-out date (YYYY-MM-DD)", type=openapi.TYPE_STRING
                                 ),
                                 openapi.Parameter(
                                     'guests', openapi.IN_QUERY, description="Filter hotels that can accommodate the specified number of guests", type=openapi.TYPE_INTEGER
                                 ),
                             ]
    )
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a hotel by ID.",
                                  manual_parameters=[
                                 openapi.Parameter(
                                     'id', openapi.IN_PATH, description="The ID of the hotel to retrieve", type=openapi.TYPE_INTEGER
                                 ),
                             ]
    )
)
class HotelViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for listing and retrieving hotels. Both regular users and admin users can access this viewset, but only read operations are allowed.
    Expected URL for listing hotels: /hotels/
    Expected URL for retrieving a hotel: /hotels/<hotel_id>/
    """
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    permission_classes = [permissions.IsAuthenticated]


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List hotel reservations.",
                                  manual_parameters=[
                                 openapi.Parameter(
                                     'hotel_id', openapi.IN_QUERY, description="Filter reservations by hotel ID", type=openapi.TYPE_INTEGER
                                 ),
                             ]
    )
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a hotel reservation by ID.",
                                  manual_parameters=[
                                 openapi.Parameter(
                                     'id', openapi.IN_PATH, description="The ID of the hotel reservation to retrieve", type=openapi.TYPE_INTEGER
                                 ),
                             ]
    )
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(operation_description="Create a hotel reservation.",
                                  request_body=HotelReservationSerializer,
                                  responses={
                                 201: openapi.Response(
                                     description="Hotel reservation created successfully",
                                     schema=openapi.Schema(
                                         type=openapi.TYPE_OBJECT,
                                         properties={
                                             "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                             "hotel_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                             "check_in": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                             "check_out": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                         }
                                     )
                                 ),
                                 400: "Invalid input data"
                             }
    )
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(operation_description="Update a hotel reservation.",
                                  request_body=HotelReservationSerializer,
                                  responses={
                                      200: openapi.Response(
                                          description="Hotel reservation updated successfully",
                                          schema=openapi.Schema(
                                              type=openapi.TYPE_OBJECT,
                                              properties={
                                                  "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "hotel_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "check_in": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                                  "check_out": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                              }
                                          )
                                      ),
                                      400: "Invalid input data"
                                  }
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(operation_description="Partially update a hotel reservation.",
                                  request_body=HotelReservationSerializer,
                                    responses={
                                        200: openapi.Response(
                                            description="Hotel reservation updated successfully",
                                            schema=openapi.Schema(
                                                type=openapi.TYPE_OBJECT,
                                                properties={
                                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                    "hotel_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                    "check_in": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                                    "check_out": openapi.Schema(type=openapi.TYPE_STRING, format="date"),
                                                }
                                            )
                                        ),
                                        400: "Invalid input data"
                                    }
                                ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Delete a hotel reservation.",
                                  responses={
                                      204: "Hotel reservation deleted successfully",
                                      404: "Hotel reservation not found"
                                  }
                                ),
)
class HotelReservationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing hotel reservations. Regular users can only see and manage their own reservations, while admin users can see and manage all reservations.
    Expected URL for creating a reservation: /hotel-reservations/
    Expected request data for creating a reservation:
    {
        "hotel_id": 1,
        "check_in": "2023-10-01",
        "check_out": "2023-10-05",
        "guests": 2
    }
    """

    queryset = HotelReservation.objects.all()
    serializer_class = HotelReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Admin users can see all reservations, regular users can only see their own reservations."""
        if getattr(self, 'swagger_fake_view', False):
            return HotelReservation.objects.none()
        user = self.request.user
        if getattr(user, "user_type", None) == "admin":
            return HotelReservation.objects.all()
        return HotelReservation.objects.filter(booking__user=user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Expected request data:
        {
            "hotel_id": 1,
            "check_in": "2023-10-01",
            "check_out": "2023-10-05",
            "guests": 2
        }"""

        data = request.data
        hotel_id = data.get("hotel_id")
        check_in = data.get("check_in")
        check_out = data.get("check_out")
        guests = int(data.get("guests", 1))

        if not hotel_id:
            return Response({"error": "hotel_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not check_in or not check_out:
            return Response(
                {"error": "check_in and check_out are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if guests < 1:
            return Response({"error": "guests must be at least 1"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            hotel = Hotel.objects.get(id=hotel_id)
        except Hotel.DoesNotExist:
            return Response({"error": "Hotel not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if check_out_date <= check_in_date:
            return Response(
                {"error": "check_out must be after check_in"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if hotel.price_per_night is None:
            return Response(
                {"error": "Hotel pricing is not available"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        number_of_nights = (check_out_date - check_in_date).days
        total_price = hotel.price_per_night * number_of_nights

        booking = BookingEngine.create_booking(
            user=request.user,
            service_type="hotel",
            total_price=total_price,
            currency=hotel.currency or "NGN",
            external_service_id=hotel.id,
        )

        reservation = HotelReservation.objects.create(
            user=request.user,
            booking=booking,
            hotel_name=hotel.hotel_name,
            check_in=check_in_date,
            check_out=check_out_date,
            guests=guests,
            total_price=total_price,
        )

        serializer = self.get_serializer(reservation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(operation_description="List hotels (admin).",
                                  manual_parameters=[
                                 openapi.Parameter(
                                     'city', openapi.IN_QUERY, description="Filter hotels by city", type=openapi.TYPE_STRING
                                 ),
                                 openapi.Parameter(
                                     'country', openapi.IN_QUERY, description="Filter hotels by country", type=openapi.TYPE_STRING
                                 ),
                             ]
    )
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve a hotel by ID (admin).",
                                  manual_parameters=[
                                 openapi.Parameter(
                                     'id', openapi.IN_PATH, description="The ID of the hotel to retrieve", type=openapi.TYPE_INTEGER
                                 ),
                             ]
    )
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(operation_description="Create a hotel (admin).",
                                  request_body=HotelSerializer,
                                  responses={
                                 201: openapi.Response(
                                     description="Hotel created successfully",
                                     schema=openapi.Schema(
                                         type=openapi.TYPE_OBJECT,
                                         properties={
                                             "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                             "hotel_name": openapi.Schema(type=openapi.TYPE_STRING),
                                             "city": openapi.Schema(type=openapi.TYPE_STRING),
                                             "address": openapi.Schema(type=openapi.TYPE_STRING),
                                             "country": openapi.Schema(type=openapi.TYPE_STRING),
                                             "price_per_night": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                                             "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                             "available_rooms": openapi.Schema(type=openapi.TYPE_INTEGER),
                                             "description": openapi.Schema(type=openapi.TYPE_STRING),
                                             "facilities": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                             "images": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                         }
                                     )
                                 ),
                                 400: "Invalid input data"
                             }
    )
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(operation_description="Update a hotel (admin).",
                                  request_body=HotelSerializer,
                                  responses={
                                      200: openapi.Response(
                                          description="Hotel updated successfully",
                                          schema=openapi.Schema(
                                              type=openapi.TYPE_OBJECT,
                                              properties={
                                                  "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "hotel_name": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "city": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "address": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "country": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "price_per_night": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                                                  "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "available_rooms": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "description": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "facilities": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                  "images": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                              }
                                          )
                                      ),
                                      400: "Invalid input data"
                                  }
                                ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(operation_description="Partially update a hotel (admin).",
                                  request_body=HotelSerializer,
                                  responses={
                                      200: openapi.Response(
                                          description="Hotel updated successfully",
                                          schema=openapi.Schema(
                                              type=openapi.TYPE_OBJECT,
                                              properties={
                                                  "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "hotel_name": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "city": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "address": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "country": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "price_per_night": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                                                  "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "available_rooms": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                  "description": openapi.Schema(type=openapi.TYPE_STRING),
                                                  "facilities": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                  "images": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                              }
                                          )
                                      ),
                                      400: "Invalid input data"
                                  }
                                ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(operation_description="Delete a hotel (admin).",
                                  responses={
                                      204: "Hotel deleted successfully",
                                      404: "Hotel not found"
                                  }
                                ),
)
class AdminHotelViewSet(viewsets.ModelViewSet):
    """This viewset is for admin users to manage hotels. It includes additional endpoints for backward compatibility with some clients.
    Only users with user_type 'admin' can access this viewset."""
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUserType]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    # Backward-compatible endpoints used by some clients
    # /hotels/create_hotel/
    @action(detail=False, methods=["post"], url_path="create_hotel")
    @swagger_auto_schema(operation_description="Create a hotel (legacy admin endpoint).",
                             request_body=HotelSerializer,
                             responses={
                                 201: openapi.Response(
                                        description="Hotel created successfully",
                                        schema=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                "hotel_name": openapi.Schema(type=openapi.TYPE_STRING),
                                                "city": openapi.Schema(type=openapi.TYPE_STRING),
                                                "address": openapi.Schema(type=openapi.TYPE_STRING),
                                                "country": openapi.Schema(type=openapi.TYPE_STRING),
                                                "price_per_night": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                                                "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                "available_rooms": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                "description": openapi.Schema(type=openapi.TYPE_STRING),
                                                "facilities": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                "images": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                            }
                                        )
                                    ),
                                 400: "Invalid input data"
                                }
                            )
    def create_hotel(self, request):
        """Expected request data:
        {
            "hotel_name": "Hotel ABC",
            "city": "Lagos",
            "address": "123 Main St",
            "country": "NG",
            "price_per_night": 10000.00,
            "currency": "NGN",
            "available_rooms": 10,
            "description": "A nice hotel in Lagos",
            "facilities": ["Free WiFi", "Pool", "Gym"],
            "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"]
        }"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # /hotels/get_hotel/<hotel_id>/
    @action(detail=False, methods=["get"], url_path="get_hotel/(?P<hotel_id>[^/.]+)")
    @swagger_auto_schema(operation_description="Retrieve a hotel by ID (legacy admin endpoint).",
                             manual_parameters=[
                                 openapi.Parameter(
                                     'hotel_id', openapi.IN_PATH, description="The ID of the hotel to retrieve", type=openapi.TYPE_INTEGER
                                 ),
                             ],
                             responses={
                                 200: openapi.Response(
                                        description="Hotel retrieved successfully",
                                        schema=openapi.Schema(
                                            type=openapi.TYPE_OBJECT,
                                            properties={
                                                "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                "hotel_name": openapi.Schema(type=openapi.TYPE_STRING),
                                                "city": openapi.Schema(type=openapi.TYPE_STRING),
                                                "address": openapi.Schema(type=openapi.TYPE_STRING),
                                                "country": openapi.Schema(type=openapi.TYPE_STRING),
                                                "price_per_night": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                                                "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                "available_rooms": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                "description": openapi.Schema(type=openapi.TYPE_STRING),
                                                "facilities": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                "images": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                            }
                                        )
                                    ),
                                 404: "Hotel not found"
                                }
                            )
    def get_hotel(self, request, hotel_id=None):
        """Expected URL: /hotels/get_hotel/1/
        This endpoint is used by some clients that expect a specific URL for fetching a hotel by ID.
        """
        hotel = self.get_queryset().filter(id=hotel_id).first()
        if not hotel:
            return Response({"error": "Hotel not found"}, status=404)
        serializer = self.get_serializer(hotel)
        return Response(serializer.data)

    # /hotels/get_all_hotels/
    @action(detail=False, methods=["get"], url_path="get_all_hotels")
    @swagger_auto_schema(operation_description="List all hotels (legacy admin endpoint).",
                             responses={
                                 200: openapi.Response(
                                        description="List of hotels retrieved successfully",
                                        schema=openapi.Schema(
                                            type=openapi.TYPE_ARRAY,
                                            items=openapi.Schema(
                                                type=openapi.TYPE_OBJECT,
                                                properties={
                                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                    "hotel_name": openapi.Schema(type=openapi.TYPE_STRING),
                                                    "city": openapi.Schema(type=openapi.TYPE_STRING),
                                                    "address": openapi.Schema(type=openapi.TYPE_STRING),
                                                    "country": openapi.Schema(type=openapi.TYPE_STRING),
                                                    "price_per_night": openapi.Schema(type=openapi.TYPE_NUMBER, format="float"),
                                                    "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                                    "available_rooms": openapi.Schema(type=openapi.TYPE_INTEGER),
                                                    "description": openapi.Schema(type=openapi.TYPE_STRING),
                                                    "facilities": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                    "images": openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING)),
                                                }
                                            )
                                        )
                                    ),
                             }
    )
    def get_all_hotels(self, request):
        """Expected URL: /hotels/get_all_hotels/
        This endpoint is used by some clients that expect a specific URL for fetching all hotels.
        """
        hotels = self.get_queryset()
        serializer = self.get_serializer(hotels, many=True)
        return Response(serializer.data)
