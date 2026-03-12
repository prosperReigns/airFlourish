from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration. This serializer is used for creating new user accounts. The password field is write-only and will be hashed when the user is created.
    Expected request data for user registration:
    {
        "email": "user@example.com",
        "password": "securepassword"
    }
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "phone_number",
            "country",
            "church",
            "zone",
            'user_type'
        ]
        read_only_fields = ["user_type"]
        extra_kwargs = {
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
            "phone_number": {"required": False, "allow_blank": True},
            "church": {"required": False, "allow_blank": True},
            "zone": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        """Creates a new user instance using the provided validated data. The password is hashed using the create_user method of the User model.
        Expected input:
        {
            "email": "user@example.com",
            "password": "securepassword"
        }
        """
        return User.objects.create_user(**validated_data)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom serializer for obtaining JWT tokens. This serializer extends the default TokenObtainPairSerializer to include additional user information in the response when a user logs in.
    Expected request data for login:
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
    }
        // other user info fields...
        """
    def validate(self, attrs):
        """Validates the user credentials and returns a token pair along with additional user information. This method overrides the default validate method to include extra fields in the response.
        Expected input:
        {
            "email": "user@example.com",
            "password": "securepassword"
        }
        """
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            raise AuthenticationFailed("Invalid email or password")

        data["user_type"] = self.user.user_type
        data["email"] = self.user.email
        data["first_name"] = self.user.first_name
        data["last_name"] = self.user.last_name
        if self.user.country:
            data["country"] = {
                "code": str(self.user.country.code),
                "name": str(self.user.country.name),
            }
        else:
            data["country"] = None
        data["phone_number"] = self.user.phone_number
        data["church"] = self.user.church
        data["zone"] = self.user.zone

        return data
    
class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile information. This serializer is used for retrieving the authenticated user's profile details. The country field is represented as a nested object with code and name."""
    country = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "first_name",
            "last_name",
            "country",
            "phone_number",
            "church",
            "zone",
            "user_type",
        ]

    def get_country(self, obj):
        """Returns the country information as a nested object with code and name for the user's profile.
        Expected output for the country field in the user profile:
        {
            "code": "US",
            "name": "United States"
        }
        """
        if not obj.country:
            return None
        return {
            "code": str(obj.country.code),
            "name": str(obj.country.name),
        }

    def get_name(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        return obj.first_name or ""
