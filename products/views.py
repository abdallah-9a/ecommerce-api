from django.core.cache import cache
from rest_framework import generics, filters
from rest_framework.response import Response
from .models import Product, Category
from .serializers import (
    ProductListSerializer,
    ProductSerializer,
    CategorySerializer,
    CategoryListSerializer,
)
from common.pagination import CustomePagination
from common.permissions import IsAdminOrReadOnly

# Create your views here.


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.select_related("category").all()
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = CustomePagination
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "category__name"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return ProductListSerializer

        return ProductSerializer
    
    def list(self, request, *args, **kwargs):
        """
        Override the default list method to implement Cache-Aside pattern.
        """
        if request.query_params.get("search"):
            return super().list(request, *args, **kwargs)

        cache_key = f"product_list_{request.get_full_path()}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=60 * 15)

        return response

    def perform_create(self, serializer):
        serializer.save()

        # Invalidation 
        cache.delete_pattern("product_list_*")


class ProductView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.select_related("category").all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]


    def perform_update(self, serializer):
        instance = serializer.save()
        cache.delete_pattern("product_list_*")
    

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete_pattern("product_list_*")


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategoryListSerializer
    pagination_class = CustomePagination
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


class CategoryView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
