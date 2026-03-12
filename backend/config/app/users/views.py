import re

from django.shortcuts import render
from django.core.cache import cache
from django_countries import countries

from django.utils.decorators import method_decorator
from rest_framework import generics
from .serializers import RegisterSerializer, CustomTokenObtainPairSerializer, UserProfileSerializer
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from .throttles import IPRateThrottle
from .authentication import BLACKLIST_PREFIX
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

User = get_user_model()

#users/register/
@method_decorator(
    name="post",
    decorator=swagger_auto_schema(operation_description="Register a new user account.",
        request_body=RegisterSerializer,
            responses={
                201: "User registered successfully",
                400: "Invalid input data"
        }
    )
)
class RegisterView(generics.CreateAPIView):
    """Endpoint for user registration. Allows anyone to create a new user account.
    Expected URL: /users/register/
    Expected request data:
    {
        "email": "user@example.com",
        "password": "securepassword"
    }
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]  # Allow anyone to register
    throttle_classes = [IPRateThrottle, AnonRateThrottle]

class LoginThrottle(UserRateThrottle):
    """Custom throttle for login attempts to prevent brute-force attacks.
    This throttle limits login attempts to 5 per minute per user and 30 per minute per IP address.
    """
    rate = "5/minute"

@method_decorator(
    name="post",
    decorator=swagger_auto_schema(
        operation_description="Authenticate and obtain JWT tokens.",
        request_body=CustomTokenObtainPairSerializer,
        responses={
            200: openapi.Response(
                description="Successful login",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "refresh": openapi.Schema(type=openapi.TYPE_STRING),
                        "access": openapi.Schema(type=openapi.TYPE_STRING),
                        "user_type": openapi.Schema(type=openapi.TYPE_STRING),
                        "email": openapi.Schema(type=openapi.TYPE_STRING),
                        "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "country": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "code": openapi.Schema(type=openapi.TYPE_STRING),
                                "name": openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        ),
                        "phone_number": openapi.Schema(type=openapi.TYPE_STRING),
                        "church": openapi.Schema(type=openapi.TYPE_STRING),
                        "zone": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            401: "Invalid credentials",
        },
    )
)
class CustomTokenObtainPairView(TokenObtainPairView):
    """Endpoint for user login that returns JWT tokens. It includes additional user information in the response.
    Expected URL: /users/login/
    Expected request data:
    {
        "email": "user@example.com",
        "password": "securepassword"
    }
    Expected response data:
    {
        "refresh": "refresh_token_here",
        "access": "access_token_here",
        "user_type": "regular",
        "email": "user@example.com"
        // other user info fields...
    }
    """
    
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle, IPRateThrottle]

#user/profile/
class ProfileView(APIView):
    """Endpoint for retrieving the authenticated user's profile information.
    Expected URL: /users/profile/
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_description="Retrieve the authenticated user's profile.",
                         responses={
            200: openapi.Response(
                description="User profile retrieved successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "email": openapi.Schema(type=openapi.TYPE_STRING),
                        "first_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "last_name": openapi.Schema(type=openapi.TYPE_STRING),
                        "country": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "code": openapi.Schema(type=openapi.TYPE_STRING),
                                "name": openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        ),
                        "phone_number": openapi.Schema(type=openapi.TYPE_STRING),
                        "church": openapi.Schema(type=openapi.TYPE_STRING),
                        "zone": openapi.Schema(type=openapi.TYPE_STRING),
                        "user_type": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            401: "Authentication credentials were not provided or are invalid",
        },
    )
    def get(self, request):
        """Returns the profile information of the authenticated user.
        Expected URL: /users/profile/
        Expected response data:
        {
            "email": "user@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "country": {
                "code": "US",
                "name": "United States"
            },
            "phone_number": "+1234567890",
            "church": "Example Church",
            "zone": "Example Zone",
            "user_type": "regular"
        }
        """
        user = request.user
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        user = request.user
        data = request.data or {}

        name = data.get("name")
        if name is not None and not str(name).strip():
            return Response({"detail": "Invalid data"}, status=400)

        country = data.get("country")
        if "country" in data:
            if not country:
                return Response({"detail": "Country is required"}, status=400)
            if not countries.lookup(country):
                return Response({"detail": "Invalid country"}, status=400)

        phone_number = data.get("phone_number")
        church = data.get("church")
        zone = data.get("zone")

        if phone_number is not None:
            if not re.fullmatch(r"\+?\d{7,15}", str(phone_number)):
                return Response({"detail": "Invalid phone number"}, status=400)
            if not church and not zone:
                return Response(
                    {"detail": "Church and zone are required when phone number is provided"},
                    status=400,
                )
            if not zone:
                return Response(
                    {"detail": "Zone is required when phone number is provided"},
                    status=400,
                )
            if not church:
                return Response(
                    {"detail": "Church is required when phone number is provided"},
                    status=400,
                )

        if church is not None and church == "":
            return Response({"detail": "Invalid church"}, status=400)

        if zone is not None and zone == "":
            return Response({"detail": "Invalid zone"}, status=400)

        if name is not None:
            user.first_name = name
        if "country" in data:
            user.country = country
        if phone_number is not None:
            user.phone_number = phone_number
        if church is not None:
            user.church = church
        if zone is not None:
            user.zone = zone

        user.save()
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)

#users/logout/
class LogoutView(APIView):
    """Endpoint for logging out users by blacklisting their refresh tokens.
    Expected request data:
    {
        "refresh": "refresh_token_here"
    }
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_description="Logout a user by blacklisting the refresh token.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="The refresh token to blacklist"),
            },            required=["refresh"],
        ),
        responses={
            205: "Logout successful",
            400: "Invalid refresh token or missing token",
        },
    )
    def post(self, request):
        """Logs out the user by blacklisting the provided refresh token. This prevents the token from being used to obtain new access tokens.
        Expected request data:
        {
            "refresh": "refresh_token_here"
        }
        """
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "Refresh token is required"}, status=401)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response({"detail": "Invalid refresh token"}, status=401)

        access_token = request.auth
        if access_token is not None:
            jti = access_token.get("jti")
            if jti:
                cache.set(
                    f"{BLACKLIST_PREFIX}{jti}",
                    True,
                    timeout=int(access_token.lifetime.total_seconds()),
                )

        return Response({"detail": "Logout successful"}, status=200)
