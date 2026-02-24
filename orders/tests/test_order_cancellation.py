from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from orders.models import Order, OrderItem
from users.models import User
from products.models import Product, Category


class OrderCancellationTestCase(APITestCase):
    """Test suite for order cancellation"""

    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123"
        )
        
        # Create category and product
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            name="Laptop",
            price=1000.00,
            stock=10,
            category=self.category
        )
        
        # Create order for user
        self.order = Order.objects.create(user=self.user, status="pending")
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=3,
            price=self.product.price
        )
        
        # Reduce stock to simulate order creation
        self.product.stock = 7  # 10 - 3
        self.product.save()
        
        self.cancel_url = reverse("cancel-order", kwargs={"pk": self.order.pk})

    def authenticate(self, user=None):
        user = user or self.user
        self.client.force_authenticate(user=user)

    def test_cancel_order_success(self):
        """Test successful order cancellation"""
        self.authenticate()
        
        response = self.client.put(self.cancel_url, {})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        
        # Verify order status changed
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "canceled")

    def test_cancel_order_stock_restored(self):
        """Test that stock is restored after cancellation"""
        self.authenticate()
        
        initial_stock = self.product.stock
        order_quantity = self.order_item.quantity
        
        response = self.client.put(self.cancel_url, {})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify stock was restored
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock + order_quantity)

    def test_cancel_order_multiple_items_stock_restored(self):
        """Test stock restoration for orders with multiple items"""
        self.authenticate()
        
        # Add another product to the order
        product2 = Product.objects.create(
            name="Mouse",
            price=25.00,
            stock=50,
            category=self.category
        )
        OrderItem.objects.create(
            order=self.order,
            product=product2,
            quantity=2,
            price=product2.price
        )
        product2.stock = 48  # Simulate stock reduction
        product2.save()
        
        initial_stock1 = self.product.stock
        initial_stock2 = product2.stock
        
        response = self.client.put(self.cancel_url, {})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify both products' stock was restored
        self.product.refresh_from_db()
        product2.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock1 + 3)
        self.assertEqual(product2.stock, initial_stock2 + 2)

    def test_cancel_order_not_pending(self):
        """Test that non-pending orders cannot be canceled"""
        self.authenticate()
        
        # Test each non-pending status
        for order_status in ["paid", "shipped", "delivered", "canceled"]:
            self.order.status = order_status
            self.order.save()
            
            initial_stock = self.product.stock
            
            response = self.client.put(self.cancel_url, {})
            
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("error", response.data)
            self.assertIn("pending", str(response.data["error"]).lower())
            
            # Verify stock was not changed
            self.product.refresh_from_db()
            self.assertEqual(self.product.stock, initial_stock)
            
            # Reset for next iteration
            self.order.status = "pending"
            self.order.save()

    def test_cancel_order_not_owner(self):
        """Test that users cannot cancel other users' orders"""
        self.authenticate(self.other_user)
        
        response = self.client.put(self.cancel_url, {})
        
        # Should return 404 because queryset filters by user
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verify order was not canceled
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")

    def test_cancel_order_unauthenticated(self):
        """Test that unauthenticated users cannot cancel orders"""
        response = self.client.put(self.cancel_url, {})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Verify order was not canceled
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")

    def test_cancel_nonexistent_order(self):
        """Test canceling an order that doesn't exist"""
        self.authenticate()
        
        url = reverse("cancel-order", kwargs={"pk": 99999})
        response = self.client.put(url, {})
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_cancel_already_canceled_order(self):
        """Test canceling an already canceled order"""
        self.authenticate()
        
        # Cancel order first time
        response = self.client.put(self.cancel_url, {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh to get updated stock after first cancellation
        self.product.refresh_from_db()
        initial_stock = self.product.stock
        
        # Try to cancel again
        response = self.client.put(self.cancel_url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify stock was not double-restored
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, initial_stock)

    def test_cancel_order_with_zero_stock_product(self):
        """Test canceling order restores stock even if product currently has 0"""
        self.authenticate()
        
        # Set product stock to 0 (all sold out)
        self.product.stock = 0
        self.product.save()
        
        response = self.client.put(self.cancel_url, {})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify stock was restored
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, self.order_item.quantity)


    def test_cancel_order_http_method(self):
        """Test that only PUT/PATCH methods work for cancellation"""
        self.authenticate()
        
        # Test GET (should not work)
        response = self.client.get(self.cancel_url)
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        
        # Test POST (should not work)
        response = self.client.post(self.cancel_url, {})
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        
        # Test DELETE (should not work)
        response = self.client.delete(self.cancel_url)
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify order is still pending
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")

