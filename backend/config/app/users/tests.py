from django.contrib.auth import get_user_model
from django.test import TestCase
from django.core.cache import cache
from app.users.serializers import RegisterSerializer, UserProfileSerializer
from config import settings
from django.test import override_settings

DISABLE_THROTTLE = override_settings(
    REST_FRAMEWORK={
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_CLASSES": [],
    }
)
class BaseTestCase(TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
# Create your tests here.
class UserModelTest(BaseTestCase):
    def test_create_user(self):
        from .models import User
        user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpassword"))
        self.assertEqual(user.user_type, "regular")
        self.assertEqual(user.phone_number, None)
        self.assertEqual(user.church, None)
        self.assertEqual(user.zone, None)

class UserRegistrationTest(BaseTestCase):
    def test_user_registration(self):
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.post("/api/users/register/", {
            "email": "test@example.com",
            "password": "testpassword",
            "country": "NG"
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["email"], "test@example.com")
        self.assertEqual(response.data["user_type"], "regular")
        self.assertEqual(response.data["phone_number"], None)
        self.assertEqual(response.data["church"], None)
        self.assertEqual(response.data["zone"], None)

class UserLoginTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_user_login(self):
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["email"], "test@example.com")
        self.assertEqual(response.data["user_type"], "regular")
        self.assertEqual(response.data["phone_number"], None)
        self.assertEqual(response.data["church"], None)
        self.assertEqual(response.data["zone"], None)

class UserProfileTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_user_profile(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)
        access_token = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        # Then, use the token to fetch the user profile
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.data["email"], "test@example.com")
        self.assertEqual(profile_response.data["user_type"], "regular")
        self.assertEqual(profile_response.data["phone_number"], None)
        self.assertEqual(profile_response.data["church"], None)
        self.assertEqual(profile_response.data["zone"], None)
    
class UserLogoutTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_user_logout(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)
        token = login_response.data["access"]

        # Then, use the token to log out
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        logout_response = client.post("/api/users/logout/", {"refresh": refresh_token})
        self.assertEqual(logout_response.status_code, 200)

        self.assertEqual(logout_response.data["detail"], "Logout successful")
        # Try to access the profile again, should fail
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 401)

class UserRegistrationThrottleTest(BaseTestCase):
    def test_registration_throttle(self):
        from rest_framework.test import APIClient
        client = APIClient()
        for i in range(6):  # Exceed the throttle limit of 5/minute
            response = client.post("/api/users/register/", {
                "email": f"test{i}@example.com",
                "password": "testpassword",
                "country": "NG"
            })
        self.assertEqual(response.status_code, 429)  # Throttle limit exceeded



class UserLoginThrottleTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_login_throttle(self):
        from rest_framework.test import APIClient
        client = APIClient()
        for i in range(6):  # Exceed the throttle limit of 5/minute
            response = client.post("/api/token/", {
                "email": "test@example.com",
                "password": "testpassword"
            })
        self.assertEqual(response.status_code, 429)  # Throttle limit exceeded

class UserIPThrottleTest(BaseTestCase):
    def test_ip_throttle(self):
        from rest_framework.test import APIClient
        client = APIClient()
        for i in range(6):  # Exceed the throttle limit of 5/minute
            response = client.post("/api/token/", {
                "email": f"test{i}@example.com",
                "password": "testpassword"
            })
        self.assertEqual(response.status_code, 429)  # Throttle limit exceeded

class UserProfileDataTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword",
            user_type="agent",
            phone_number="1234567890",
            country="US",
            church="Test Church",
            zone="Test Zone"
        )
    def test_user_profile_data(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)
        token = login_response.data["access"]
        # Then, use the token to fetch the user profile
        client.credentials(HTTP_AUTHORIZATION="Bearer " + token)
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.data["email"], "test@example.com")
        self.assertEqual(profile_response.data["user_type"], "agent")
        self.assertEqual(profile_response.data["phone_number"], "1234567890")
        self.assertEqual(profile_response.data["church"], "Test Church")
        self.assertEqual(profile_response.data["zone"], "Test Zone")

class UserLogoutInvalidTokenTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_logout_invalid_token(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # Try to log out with an invalid token
        client.credentials(HTTP_AUTHORIZATION="Bearer " + "invalidtoken")
        logout_response = client.post("/api/users/logout/")
        self.assertEqual(logout_response.status_code, 401)  # Unauthorized due to invalid token
        self.assertEqual(logout_response.data["detail"], "Invalid token")

class UserLogoutNoTokenTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_logout_no_token(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # Try to log out without providing a token
        logout_response = client.post("/api/users/logout/")
        self.assertEqual(logout_response.status_code, 401)  # Unauthorized due to missing token
        self.assertEqual(logout_response.data["detail"], "Authentication credentials were not provided.")

class UserProfileUnauthorizedTest(BaseTestCase):
    def test_profile_unauthorized(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # Try to access the profile without logging in
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 401)  # Unauthorized due to missing token
        self.assertEqual(profile_response.data["detail"], "Authentication credentials were not provided.")

class UserProfileInvalidTokenTest(BaseTestCase):
    def test_profile_invalid_token(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # Try to access the profile with an invalid token
        client.credentials(HTTP_AUTHORIZATION="Bearer " + "invalidtoken")
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 401)  # Unauthorized due to invalid token
        self.assertEqual(profile_response.data["detail"], "Invalid token")

class UserRegistrationInvalidDataTest(BaseTestCase):
    def test_registration_invalid_data(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # Try to register with missing email
        response = client.post("/api/users/register/", {
            "password": "testpassword",
            "country": "NG"
        })
        self.assertEqual(response.status_code, 400)  # Bad request due to missing email
        self.assertIn("email", response.data)
        # Try to register with missing password
        response = client.post("/api/users/register/", {
            "email": "test@example.com",
            "country": "NG"
        })
        self.assertEqual(response.status_code, 400)  # Bad request due to missing password
        self.assertIn("password", response.data)

class UserLoginInvalidDataTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_login_invalid_data(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # Try to log in with missing email
        response = client.post("/api/token/", {
            "password": "testpassword"
        })
        self.assertEqual(response.status_code, 400)  # Bad request due to missing email
        self.assertIn("email", response.data)
        # Try to log in with missing password
        response = client.post("/api/token/", {
            "email": "test@example.com"
        })
        self.assertEqual(response.status_code, 400)  # Bad request due to missing password
        self.assertIn("password", response.data)

class UserLoginInvalidCredentialsTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_login_invalid_credentials(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # Try to log in with incorrect password
        response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        self.assertEqual(response.status_code, 401)  # Unauthorized due to invalid credentials
        self.assertEqual(response.data["detail"], "Invalid email or password")
        # Try to log in with non-existent email
        response = client.post("/api/token/", {
            "email": "nonexistent@example.com",
            "password": "testpassword"
        })
        self.assertEqual(response.status_code, 401)  # Unauthorized due to invalid credentials
        self.assertEqual(response.data["detail"], "Invalid email or password")

class UserLogoutInvalidRefreshTokenTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_logout_invalid_refresh_token(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to log out with an invalid refresh token
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        logout_response = client.post("/api/users/logout/", {"refresh": "invalidrefresh"})
        self.assertEqual(logout_response.status_code, 401)  # Unauthorized due to invalid refresh token
        self.assertEqual(logout_response.data["detail"], "Invalid refresh token")

class UserLogoutMissingRefreshTokenTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_logout_missing_refresh_token(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to log out without providing a refresh token
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        logout_response = client.post("/api/users/logout/")
        self.assertEqual(logout_response.status_code, 401)  # Unauthorized due to missing refresh token
        self.assertEqual(logout_response.data["detail"], "Refresh token is required")

class UserLogoutInvalidTokenFormatTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_logout_invalid_token_format(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to log out with an invalid refresh token format
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        logout_response = client.post("/api/users/logout/", {"refresh": "invalid.refresh.token"})
        self.assertEqual(logout_response.status_code, 401)  # Unauthorized due to invalid refresh token
        self.assertEqual(logout_response.data["detail"], "Invalid refresh token")

class UserProfileInvalidCountryTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_profile_invalid_country(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to update profile with an invalid country
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "country": "InvalidCountry"
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to invalid country
        self.assertEqual(profile_response.data["detail"], "Invalid country")

class UserProfileMissingCountryTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_profile_missing_country(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to update profile without providing a country
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "country": ""
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to missing country
        self.assertEqual(profile_response.data["detail"], "Country is required")

class UserProfileInvalidPhoneNumberTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_profile_invalid_phone_number(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to update profile with an invalid phone number
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "phone_number": "invalid-phone-number"
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to invalid phone number
        self.assertEqual(profile_response.data["detail"], "Invalid phone number")
    
class UserProfileMissingPhoneNumberTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_profile_missing_phone_number(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]
        # Try to update profile without providing a phone number
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "name": "Test User"
        })
        self.assertEqual(profile_response.status_code, 200)  # Successful update without phone number
        self.assertEqual(profile_response.data["phone_number"], None)

class UserProfileInvalidChurchTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_profile_invalid_church(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to update profile with an invalid church
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "church": ""
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to invalid church
        self.assertEqual(profile_response.data["detail"], "Invalid church")

class UserProfileMissingChurchTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_profile_missing_church(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to update profile without providing a church
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "name": "Test User"
        })
        self.assertEqual(profile_response.status_code, 200)  # Successful update without church
        self.assertEqual(profile_response.data["church"], None)

class UserProfileInvalidZoneTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_profile_invalid_zone(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to update profile with an invalid zone
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "zone": ""
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to invalid zone
        self.assertEqual(profile_response.data["detail"], "Invalid zone")

class UserProfileMissingZoneTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_profile_missing_zone(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to update profile without providing a zone
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "name": "Test User"
        })
        self.assertEqual(profile_response.status_code, 200)  # Successful update without zone
        self.assertEqual(profile_response.data["zone"], None)

class UserProfileInvalidDataTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_profile_invalid_data(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to update profile with invalid data
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "name": ""  # Invalid name (empty string)
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to invalid data
        self.assertEqual(profile_response.data["detail"], "Invalid data")

class UserProfileValidDataTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_profile_valid_data(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to update profile with valid data
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "name": "Test User"
        })
        self.assertEqual(profile_response.status_code, 200)  # Successful update with valid data
        self.assertEqual(profile_response.data["name"], "Test User")

class UserProfileNoChangesTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
    def test_profile_no_changes(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "test@example.com",
            "password": "testpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]

        # Try to update profile without making any changes
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "name": "Test User"
        })
        self.assertEqual(profile_response.status_code, 200)  # Successful update with no changes
        self.assertEqual(profile_response.data["name"], "Test User")

class UserProfileInvalidTokenTest(BaseTestCase):
    def test_profile_invalid_token(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # Try to access the profile with an invalid token
        client.credentials(HTTP_AUTHORIZATION="Bearer " + "invalidtoken")
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 401)  # Unauthorized due to invalid token
        self.assertEqual(profile_response.data["detail"], "Invalid token")

class UserProfileMissingTokenTest(BaseTestCase):
    def test_profile_missing_token(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # Try to access the profile without providing a token
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 401)  # Unauthorized due to missing token
        self.assertEqual(profile_response.data["detail"], "Authentication credentials were not provided.")

class UserProfileNonExistentUserTest(BaseTestCase):
    def test_profile_non_existent_user(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # Try to access the profile of a non-existent user
        client.credentials(HTTP_AUTHORIZATION="Bearer " + "nonexistenttoken")
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 401)  # Unauthorized due to invalid token
        self.assertEqual(profile_response.data["detail"], "Invalid token")

class UserProfileInactiveUserTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword"
        )
        self.user.is_active = False
        self.user.save()
    def test_profile_inactive_user(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # Try to access the profile of an inactive user
        client.credentials(HTTP_AUTHORIZATION="Bearer " + "inactivetoken")
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 401)  # Unauthorized due to invalid token
        self.assertEqual(profile_response.data["detail"], "Invalid token")

class UserProfileAdminUserTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="admin@example.com",
            password="adminpassword",
            is_staff=True
        )
    def test_profile_admin_user(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "admin@example.com",
            "password": "adminpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]
        # Try to access the profile of an admin user
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 200)  # Successful access to admin profile
        self.assertEqual(profile_response.data["email"], "admin@example.com")
        self.assertEqual(profile_response.data["user_type"], "regular")  # Admin users are still regular type
        self.assertEqual(profile_response.data["phone_number"], None)
        self.assertEqual(profile_response.data["church"], None)
        self.assertEqual(profile_response.data["zone"], None)

class UserProfileAgentUserTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="agent@example.com",
            password="agentpassword",
            user_type="agent"
        )
    def test_profile_agent_user(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "agent@example.com",
            "password": "agentpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]
        # Try to access the profile of an agent user
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 200)  # Successful access to agent profile
        self.assertEqual(profile_response.data["email"], "agent@example.com")
        self.assertEqual(profile_response.data["user_type"], "agent")
        self.assertEqual(profile_response.data["phone_number"], None)
        self.assertEqual(profile_response.data["church"], None)
        self.assertEqual(profile_response.data["zone"], None)

class UserProfileRegularUserTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="regular@example.com",
            password="regularpassword",
            user_type="regular"
        )
    def test_profile_regular_user(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "regular@example.com",
            "password": "regularpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]
        # Try to access the profile of a regular user
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 200)  # Successful access to regular profile
        self.assertEqual(profile_response.data["email"], "regular@example.com")
        self.assertEqual(profile_response.data["user_type"], "regular")
        self.assertEqual(profile_response.data["phone_number"], None)
        self.assertEqual(profile_response.data["church"], None)
        self.assertEqual(profile_response.data["zone"], None)

class UserProfileMultipleUpdatesTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="multiple@example.com",
            password="multiplepassword",
            user_type="regular"
        )
    def test_profile_multiple_updates(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "multiple@example.com",
            "password": "multiplepassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]
        # Try to access the profile of a regular user
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 200)  # Successful access to regular profile
        self.assertEqual(profile_response.data["email"], "multiple@example.com")
        self.assertEqual(profile_response.data["user_type"], "regular")
        self.assertEqual(profile_response.data["phone_number"], None)
        self.assertEqual(profile_response.data["church"], None)
        self.assertEqual(profile_response.data["zone"], None)

class UserProfileDataPersistenceTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="persistence@example.com",
            password="persistencepassword",
            user_type="regular"
        )
    def test_profile_data_persistence(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "persistence@example.com",
            "password": "persistencepassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]
        # Try to access the profile of a regular user
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 200)  # Successful access to regular profile
        self.assertEqual(profile_response.data["email"], "persistence@example.com")
        self.assertEqual(profile_response.data["user_type"], "regular")
        self.assertEqual(profile_response.data["phone_number"], None)
        self.assertEqual(profile_response.data["church"], None)
        self.assertEqual(profile_response.data["zone"], None)

class UserProfileDataUpdateTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="update@example.com",
            password="updatepassword",
            user_type="regular"
        )
    def test_profile_data_update(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "update@example.com",
            "password": "updatepassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]
        # Try to access the profile of a regular user
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 200)  # Successful access to regular profile
        self.assertEqual(profile_response.data["email"], "update@example.com")
        self.assertEqual(profile_response.data["user_type"], "regular")
        self.assertEqual(profile_response.data["phone_number"], None)
        self.assertEqual(profile_response.data["church"], None)
        self.assertEqual(profile_response.data["zone"], None)
        # Update the profile with new data
        update_response = client.patch("/api/users/profile/", {
            "phone_number": "1234567890",
            "church": "Test Church",
            "zone": "Test Zone"
        })
        self.assertEqual(update_response.status_code, 200)  # Successful profile update
        self.assertEqual(update_response.data["phone_number"], "1234567890")
        self.assertEqual(update_response.data["church"], "Test Church")
        self.assertEqual(update_response.data["zone"], "Test Zone")
        # Verify that the updated data is persisted        profile_response = client.get("/api/users/profile/")
        self.assertEqual(profile_response.status_code, 200)  # Successful access to regular profile
        self.assertEqual(profile_response.data["email"], "update@example.com")
        self.assertEqual(profile_response.data["user_type"], "regular")
        self.assertEqual(profile_response.data["phone_number"], "1234567890")
        self.assertEqual(profile_response.data["church"], "Test Church")
        self.assertEqual(profile_response.data["zone"], "Test Zone")

class UserProfileDataValidationTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="validation@example.com",
            password="validationpassword",
            user_type="regular"
        )
    def test_profile_data_validation(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "validation@example.com",
            "password": "validationpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login 
        access_token = login_response.data["access"]
        # Try to update profile with invalid data
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "phone_number": "invalid-phone-number"
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to invalid phone number
        self.assertEqual(profile_response.data["detail"], "Invalid phone number")
        profile_response = client.patch("/api/users/profile/", {
            "church": ""  # Invalid church (empty string)
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to invalid church
        self.assertEqual(profile_response.data["detail"], "Invalid church")
        profile_response = client.patch("/api/users/profile/", {
            "zone": ""  # Invalid zone (empty string)
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to invalid zone
        self.assertEqual(profile_response.data["detail"], "Invalid zone")

class UserProfileDataValidationMissingFieldsTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="missingfields@example.com",
            password="missingfieldspassword",
            user_type="regular"
        )
    def test_profile_data_validation_missing_fields(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "missingfields@example.com",
            "password": "missingfieldspassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]
        # Try to update profile with missing fields
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "phone_number": "1234567890"
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to missing fields
        self.assertEqual(profile_response.data["detail"], "Church and zone are required when phone number is provided")
        profile_response = client.patch("/api/users/profile/", {
            "phone_number": "1234567890",
            "church": "Test Church"
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to missing zone
        self.assertEqual(profile_response.data["detail"], "Zone is required when phone number is provided")
        profile_response = client.patch("/api/users/profile/", {
            "phone_number": "1234567890",
            "zone": "Test Zone"
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to missing church
        self.assertEqual(profile_response.data["detail"], "Church is required when phone number is provided")
        self.assertEqual(profile_response.data["detail"], "Church is required when phone number is provided")

class UserProfileDataValidationTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="validation@example.com",
            password="validationpassword",
            user_type="regular"
        )
    def test_profile_data_validation(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "validation@example.com",
            "password": "validationpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]
        # Try to update profile with invalid data
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "phone_number": "invalid-phone-number"
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to invalid phone number
        self.assertEqual(profile_response.data["detail"], "Invalid phone number")
        profile_response = client.patch("/api/users/profile/", {
            "church": ""  # Invalid church (empty string)
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to invalid church
        self.assertEqual(profile_response.data["detail"], "Invalid church")
        profile_response = client.patch("/api/users/profile/", {
            "zone": ""  # Invalid zone (empty string)
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to invalid zone
        self.assertEqual(profile_response.data["detail"], "Invalid zone")

class UserProfileDataValidationMissingFieldsTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="missingfields@example.com",
            password="missingfieldspassword",
            user_type="regular"
        )
    def test_profile_data_validation_missing_fields(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "missingfields@example.com",
            "password": "missingfieldspassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]
        # Try to update profile with missing fields
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "phone_number": "1234567890"
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to missing fields
        self.assertEqual(profile_response.data["detail"], "Church and zone are required when phone number is provided")
        profile_response = client.patch("/api/users/profile/", {
            "phone_number": "1234567890",
            "church": "Test Church"
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to missing
        self.assertEqual(profile_response.data["detail"], "Zone is required when phone number is provided")
        profile_response = client.patch("/api/users/profile/", {
            "phone_number": "1234567890",
            "zone": "Test Zone"
        })
        self.assertEqual(profile_response.status_code, 400)  # Bad Request due to missing
        self.assertEqual(profile_response.data["detail"], "Church is required when phone number is provided")

class UserProfileDataValidationSuccessTest(BaseTestCase):
    def setUp(self):
        from .models import User
        self.user = User.objects.create_user(
            email="success@example.com",
            password="successpassword",
            user_type="regular"
        )
    def test_profile_data_validation_success(self):
        from rest_framework.test import APIClient
        client = APIClient()
        # First, log in to get the token
        login_response = client.post("/api/token/", {
            "email": "success@example.com",
            "password": "successpassword"
        })
        self.assertEqual(login_response.status_code, 200)  # Successful login
        access_token = login_response.data["access"]
        # Try to update profile with valid data
        client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)
        profile_response = client.patch("/api/users/profile/", {
            "phone_number": "1234567890",
            "church": "Test Church",
            "zone": "Test Zone"
        })
        self.assertEqual(profile_response.status_code, 200)  # Successful profile update
        self.assertEqual(profile_response.data["phone_number"], "1234567890")
        self.assertEqual(profile_response.data["church"], "Test Church")
        self.assertEqual(profile_response.data["zone"], "Test Zone")


class RegisterSerializerTests(BaseTestCase):
    def test_register_serializer_creates_user(self):
        payload = {
            "email": "serializer@example.com",
            "password": "password123",
            "country": "NG",
        }
        serializer = RegisterSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.email, "serializer@example.com")
        self.assertTrue(user.check_password("password123"))


class UserProfileSerializerTests(BaseTestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="profileserializer@example.com",
            password="password123",
            country="NG",
        )

    def test_user_profile_serializer_outputs_expected_fields(self):
        data = UserProfileSerializer(self.user).data
        self.assertEqual(data["email"], "profileserializer@example.com")
        self.assertEqual(data["user_type"], "regular")
        self.assertEqual(data["country"]["code"], str(self.user.country.code))
        self.assertEqual(data["country"]["name"], str(self.user.country.name))


class RegisterSerializerValidationTests(BaseTestCase):
    def test_register_serializer_missing_email(self):
        serializer = RegisterSerializer(
            data={
                "password": "password123",
                "country": "NG",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_register_serializer_invalid_email(self):
        serializer = RegisterSerializer(
            data={
                "email": "not-an-email",
                "password": "password123",
                "country": "NG",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_register_serializer_missing_password(self):
        serializer = RegisterSerializer(
            data={
                "email": "missingpass@example.com",
                "country": "NG",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_register_serializer_missing_country(self):
        serializer = RegisterSerializer(
            data={
                "email": "missingcountry@example.com",
                "password": "password123",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("country", serializer.errors)
