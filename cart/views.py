from django.core.exceptions import ValidationError
from rest_framework import views, status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from products.models import Product
from .services import RedisCart
from .serializers import CartItemInputSerializer, CartItemUpdateSerializer

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

    def create(self, request):
        serializer = CartItemInputSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data['product_id']
            quantity = serializer.validated_data.get('quantity', 1)
            
            try:
                cart = RedisCart(request.user)
                cart.add(product_id, quantity)

                return Response({"message": "Item added to your cart"}, status=status.HTTP_201_CREATED)
            except Product.DoesNotExist:
                return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        serializer = CartItemUpdateSerializer(data=request.data)
        if serializer.is_valid():
            quantity = serializer.validated_data['quantity']

            try:
                cart = RedisCart(request.user)
                cart.update(product_id=pk, quantity=quantity)
                
                if quantity == 0:
                    return Response({"message": "Item removed from cart"}, status=status.HTTP_200_OK)
                return Response({"message": "Quantity updated"}, status=status.HTTP_200_OK)
            except Product.DoesNotExist:
                return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)
            except ValidationError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        cart = RedisCart(request.user)
        cart.remove(product_id=pk)
        return Response({"message": "Item removed"}, status=status.HTTP_204_NO_CONTENT)