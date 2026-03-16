from django.urls import path
from .views import UserTransactionListView, AdminTransactionListView

urlpatterns = [
    path("my-transactions/", UserTransactionListView.as_view()),
    path("admin/transactions/", AdminTransactionListView.as_view()),
]