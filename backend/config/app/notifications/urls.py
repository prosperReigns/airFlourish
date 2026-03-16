from django.urls import path
from .views import NotificationListView, MarkNotificationReadView

urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications"),
    path("read/<int:notification_id>/", MarkNotificationReadView.as_view(), name="mark_notification_read"),
]