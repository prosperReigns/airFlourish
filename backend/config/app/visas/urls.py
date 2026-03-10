from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import VisaApplicationViewSet, VisaApprovalView

router = DefaultRouter()
router.register(r'visas', VisaApplicationViewSet, basename='visa')

urlpatterns = router.urls  + [
    path("approve/<int:visa_id>/", VisaApprovalView.as_view(), name="visa-approve"),
]
