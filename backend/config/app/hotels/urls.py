from rest_framework.routers import DefaultRouter
from .views import AdminHotelViewSet, HotelReservationViewSet, HotelViewSet

router = DefaultRouter()
router.register(r'admin-hotels', AdminHotelViewSet, basename='adminhotel')
router.register(r'hotels', HotelViewSet, basename='hotel')
router.register(r'hotel-reservations', HotelReservationViewSet, basename='hotelreservation')

urlpatterns = router.urls
