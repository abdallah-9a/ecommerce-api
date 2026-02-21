from django.shortcuts import render
from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import generics, status, filters
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .serializers import OrderSerializer, UpdateOrderStatusSerializer
from .models import Order, OrderItem
from products.models import Product
from cart.services import RedisCart
from common.pagination import CustomePagination

# Create your views here.


class OrderListCreateView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomePagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["status"]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):

        cart = RedisCart(self.request.user)
        cart_data = cart.get_cart_details()
        items = cart_data.get("items", [])

        if not items:
            raise ValidationError("Your Cart is Empty")

        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                order = serializer.save(user=self.request.user)

                for item in items:
                    product_id = item.get("product_id")
                    quantity = item.get("quantity")

                    try:
                        product = Product.objects.select_for_update().get(id=product_id)

                    except Product.DoesNotExist:
                        raise ValidationError(
                            f"Product with id {product_id} does not exist"
                        )

                    if product.stock < quantity:
                        raise ValidationError(
                            f"Not enough stock for product {product.name}, Only {product.stock} left"
                        )

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        price=product.price,
                    )

                    product.stock -= quantity
                    product.save()

                cart.clear()

        except ValidationError as e:
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {
                    "error": "An error occurred while processing your order.",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)


class OrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class UpdateOrderStatusView(generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = UpdateOrderStatusSerializer
    permission_classes = [IsAdminUser]

    def perform_update(self, serializer):
        order = self.get_object()
        new_status = serializer.validated_data["status"]
        allowed = Order.VALID_STATUS_TRANSITIONS.get(order.status, [])
        if new_status not in allowed:
            raise ValidationError(
                f"Cannot transition from '{order.status}' to '{new_status}'. "
                f"Allowed transitions: {allowed}"
            )
        serializer.save()


class CancelOrderView(generics.UpdateAPIView):
    serializer_class = UpdateOrderStatusSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    def update(self, request, *args, **kwargs):
        order = self.get_object()
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order.id)
                if order.status != "pending":
                    raise ValidationError("Only pending order can be canceled")
                for item in order.items.select_related("product").all():
                    product = Product.objects.select_for_update().get(
                        id=item.product.id
                    )

                    product.stock += item.quantity
                    product.save()

                order.status = "canceled"
                order.save()

        except ValidationError as e:
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response(
                {
                    "error": "An error occurred while canceling your order.",
                    "details": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"detail": "Your order has been canceled"}, status=status.HTTP_200_OK
        )
