from django.urls import path
from .views import CartView, CartItemsView

urlpatterns = [
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/items/", CartItemsView.as_view({"post": "create"}), name="cart-items"),
    path("cart/items/<int:pk>/", CartItemsView.as_view({"put": "update", "delete": "destroy"}), name="cart-item-detail"),
]
