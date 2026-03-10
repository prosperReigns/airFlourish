from django.shortcuts import render

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
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from .throttles import IPRateThrottle
from drf_yasg.utils import swagger_auto_schema

User = get_user_model()

#users/register/
@method_decorator(
    name="post",
    decorator=swagger_auto_schema(operation_description="Register a new user account."),
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
    decorator=swagger_auto_schema(operation_description="Authenticate and obtain JWT tokens."),
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

    @swagger_auto_schema(operation_description="Retrieve the authenticated user's profile.")
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

#users/logout/
class LogoutView(APIView):
    """Endpoint for logging out users by blacklisting their refresh tokens.
    Expected request data:
    {
        "refresh": "refresh_token_here"
    }
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(operation_description="Logout a user by blacklisting the refresh token.")
    def post(self, request):
        """Logs out the user by blacklisting the provided refresh token. This prevents the token from being used to obtain new access tokens.
        Expected request data:
        {
            "refresh": "refresh_token_here"
        }
        """
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token required"}, status=400)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Logout successful"}, status=205)
        except Exception:
            return Response({"error": "Invalid refresh token"}, status=400)
