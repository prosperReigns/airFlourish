import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import sys
import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", 'django-insecure-6ophipqh)6ub6p+$&e713pv*ja79)3_%%6)=+w&n*kul$nf2d*')

# Application definition
INSTALLED_APPS = [
    'django_prometheus',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "rest_framework",
    "corsheaders",
    "app.users",
    "app.bookings",
    "app.flights",
    "app.hotels",
    "app.visas",
    "app.payments",
    "app.transport",
    "app.notifications",
    "app.transactions",
    "app.wallets",
    "app.core",
    "app.inventory",
    "app.pricing",
    "app.maintenance",
    "app.events",
    "app.api_keys",
    "app.security",
    "app.search_security",
    "app.audit",
    'rest_framework_simplejwt.token_blacklist',
    'drf_yasg',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'app.core.middleware.IdempotencyMiddleware',
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
    "app.api_keys.middleware.APIKeyMiddleware",
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# JWT settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=360),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "app.users.authentication.CustomJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "app.core.pagination.DefaultPagination",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/minute",
        "user": "100/minute",
        "ip": "30/minute",
        "hotel_search": "10/minute",
        "flight_search": "10/minute",
    }
}

USING_TESTS = "test" in sys.argv
if USING_TESTS:
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].update({
        "anon": "5/minute",
        "user": "5/minute",
        "ip": "5/minute",
    })
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static & media
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Swagger
SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': False,
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    }
}

# External APIs
FLUTTERWAVE_SECRET_KEY = os.getenv("FLUTTERWAVE_SECRET_KEY")
FLUTTERWAVE_SECRET_HASH = os.getenv("FLUTTERWAVE_SECRET_HASH", "your_secret_hash_here")
PAYMENT_REDIRECT_URL = os.getenv(
    "PAYMENT_REDIRECT_URL",
    "http://127.0.0.1:8000/api/payments/redirect/",
)
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
BOOKING_RAPIDAPI_KEY = os.getenv("BOOKING_RAPIDAPI_KEY")
BOOKING_RAPIDAPI_HOST = os.getenv("BOOKING_RAPIDAPI_HOST")

# Currency settings
# Map country codes to preferred display/charge currency.
COUNTRY_CURRENCY_MAP = {
    "NG": "NGN",
}
# Flutterwave bank transfer support is currency-limited (e.g., NGN/GHS).
BANK_TRANSFER_SUPPORTED_CURRENCIES = ["NGN", "GHS"]

# Visa settings
VISA_TYPES_DEFAULT = ["Tourist", "Business"]
VISA_TYPES_BY_COUNTRY = {
    "NG": ["Tourist", "Business", "Student", "Work"],
}
REQUIRED_VISA_DOCUMENT_TYPES = ["passport"]
VISA_DEFAULT_PROCESSING_DAYS = 7
VISA_TYPE_REQUIRED_DOCUMENTS = {
    "tourist": ["passport", "photo", "travel_itinerary", "bank_statement"],
    "business": ["passport", "invitation_letter", "company_letter", "bank_statement"],
    "student": ["passport", "acceptance_letter", "transcript", "financial_proof"],
    "work": ["passport", "employment_letter", "cv", "qualification_certificates"],
}

# Cache settings (flight search/payment context)
FLIGHT_OFFER_CACHE_TTL = 60 * 60  # 1 hour
FLIGHT_PAYMENT_CONTEXT_TTL = 6 * 60 * 60  # 6 hours

# Idempotency + hotel reservation holds
IDEMPOTENCY_TTL_SECONDS = 24 * 60 * 60
HOTEL_RESERVATION_HOLD_MINUTES = 30

# Celery
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/0'
CELERY_TIMEZONE = "Africa/Lagos"
CELERY_BEAT_SCHEDULE = {
    "expire-hotel-reservation-holds": {
        "task": "app.hotels.tasks.expire_hotel_reservation_holds",
        "schedule": 300.0,
    }
}

RECAPTCHA_SECRET_KEY = ""

LOGGING = {

    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {

        "standard": {

            "format": "[%(levelname)s] %(asctime)s %(name)s: %(message)s",

        }

    },

    "handlers": {

        "console": {

            "class": "logging.StreamHandler",

            "formatter": "standard",

        }

    },

    "root": {

        "handlers": ["console"],

        "level": "INFO",

    },
}
