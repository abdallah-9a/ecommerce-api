from rest_framework import serializers
from .models import Product, Category


class ProductListSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        queryset=Category.objects.all(), slug_field="name"
    )

    class Meta:
        model = Product
        fields = ["id", "name", "slug", "category", "price", "image"]


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        queryset=Category.objects.all(), slug_field="name"
    )

    class Meta:
        model = Product
        fields = "__all__"


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class CategorySerializer(serializers.ModelSerializer):
    products = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "products"]
