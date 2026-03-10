"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from app.users.views import CustomTokenObtainPairView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.contrib import admin
from django.urls import path, re_path, include

from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from django.contrib.staticfiles.urls import staticfiles_urlpatterns 

schema_view = get_schema_view(
   openapi.Info(
      title="Airflourish Travel API",
      default_version='v1',
      description="""
        Welcome to the Airflourish Travel API.

        This API allows clients to interact with the travel platform.

        Features include:
        - Flight search and booking
        - Hotel search and reservation
        - Transport booking
        - Visa assistance
        - Payment processing

        Authentication:
        This API uses JWT authentication.

        Include the token in the header:

        Authorization: Bearer <token>
        """,
      terms_of_service="https://www.example.com/terms/",
      contact=openapi.Contact(email="support@travelapp.com"),
      license=openapi.License(name="MIT License"),
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/users/', include('app.users.urls')),
    path('api/bookings/', include('app.bookings.urls')),
    path('api/flights/', include('app.flights.urls')),
    path('api/visas/', include('app.visas.urls')),
    path('api/hotels/', include('app.hotels.urls')),
    path('api/transport/', include('app.transport.urls')),
    path('api/payments/', include('app.payments.urls')),
    #jwt
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Swagger documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
        schema_view.without_ui(cache_timeout=0),
        name='schema-json'),

    path('swagger/',
        schema_view.with_ui('swagger', cache_timeout=0),
        name='schema-swagger-ui'),

    path('redoc/',
        schema_view.with_ui('redoc', cache_timeout=0),
        name='schema-redoc'),
]

urlpatterns += staticfiles_urlpatterns()