from django.urls import path
from .views import (
    OrderListCreateView,
    OrderDetailView,
    UpdateOrderStatusView,
    CancelOrderView,
    
)

urlpatterns = [
    path("", OrderListCreateView.as_view(), name="orders"),
    path("<int:pk>/", OrderDetailView.as_view(), name="order-detail"),
    path("<int:pk>/status/", UpdateOrderStatusView.as_view(), name="order-status"),
    path("<int:pk>/cancel/", CancelOrderView.as_view(), name="cancel-order"),
]
