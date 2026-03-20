from django.db.models import F
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Inventory
from .permissions import IsAdminOrReadOnlyUserType
from .serializers import InventorySerializer


@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_description="List inventory entries.",
        responses={200: InventorySerializer(many=True)},
    ),
)
@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(operation_description="Retrieve inventory details."),
)
class InventoryViewSet(viewsets.ModelViewSet):
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnlyUserType]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Inventory.objects.none()
        user = self.request.user
        queryset = Inventory.objects.annotate(available_quantity=F("available_quantity"))
        if getattr(user, "user_type", None) == "admin":
            return queryset
        return queryset.filter(available_quantity__gt=0)
