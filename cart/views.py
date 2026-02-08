from django.shortcuts import get_object_or_404
from rest_framework import views, status,viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .services import RedisCart
from .serializers import CartItemSerializer
from products.models import Product

# Create your views here.


class CartView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = RedisCart(request.user)
        data = cart.get_cart_details()
        return Response(data)
    
    def delete(self, request):
        cart = RedisCart(request.user)
        cart.clear()
        return Response({"message": "Cart cleared"}, status=status.HTTP_204_NO_CONTENT)


class CartItemsView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CartItemSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.validated_data['product']
            quantity = serializer.validated_data.get('quantity', 1)
            
            cart = RedisCart(request.user)
            cart.add(product.id, quantity)

            return Response({"message": "Item added to your cart"}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        quantity = request.data.get('quantity')
        if not quantity:
            return Response({"error": "Quantity is required"}, status=400)

        product = get_object_or_404(Product, id=pk)
        cart = RedisCart(request.user)
        cart.update(product_id=pk, quantity=int(quantity))
        return Response({"message": "Quantity updated"})

    def delete(self, request, pk):
        cart = RedisCart(request.user)
        cart.remove(product_id=pk)
        return Response({"message": "Item removed"}, status=status.HTTP_204_NO_CONTENT)