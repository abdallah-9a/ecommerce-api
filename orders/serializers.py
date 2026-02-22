from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "quantity", "price"]


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES, read_only=True)
    
    class Meta:
        model = Order
        fields = ["id", "user", "items", "status", "total_price", "created_at", "updated_at"]

    def get_total_price(self, obj):
        if hasattr(obj, "annotated_total") and obj.annotated_total is not None:
            return obj.annotated_total
        return obj.total_price()


class UpdateOrderStatusSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES, required=True)
    
    class Meta:
        model = Order
        fields = ["status"]
