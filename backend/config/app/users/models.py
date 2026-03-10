from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django_countries.fields import CountryField

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """Creates and saves a User with the given email and password.
        This method is used for creating regular user accounts. It requires an email and password, and can accept additional fields through extra_fields. The email is normalized and the password is hashed before saving the user instance.
        Expected input:
        {
            "email": "user@example.com",
            "password": "securepassword"
        }
        """
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Creates and saves a superuser with the given email and password.
        This method is used for creating admin user accounts. It sets the is_staff and is_superuser flags to True, and requires an email and password. The email is normalized and the password is hashed before saving the user instance.
        Expected input:
        {
            "email": "admin@example.com",
            "password": "securepassword"
        }
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model for the application. This model extends the default AbstractUser and replaces the username field with an email field for authentication. It also includes additional fields such as user_type, phone_number, country, church, and zone to store more information about the user.
    The user_type field is used to differentiate between regular users, agents, and admin users.
    Expected user types:
    - regular: Regular user with standard access
    - agent: User with permissions to manage bookings and hotels
    - admin: User with full access to manage the application
    """
    username = None  # 🔥 remove username completely

    USER_TYPE_CHOICES = (
        ("regular", "Regular"),
        ("agent", "Agent"),
        ("admin", "Admin"),
    )

    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default="regular")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    country = CountryField(blank=False, null=False)
    church = models.CharField(max_length=255, blank=True, null=True)
    zone = models.CharField(max_length=255, blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        """Returns the string representation of the user, which is the email address. This method is used for displaying the user in the admin interface and other parts of the application where a string representation is needed."""
        return self.email