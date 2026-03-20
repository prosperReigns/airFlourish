from rest_framework.routers import DefaultRouter

from .views import CarRentalViewSet

router = DefaultRouter()
router.register(r"rentals", CarRentalViewSet, basename="car-rental")

urlpatterns = router.urls
