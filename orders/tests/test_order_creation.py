from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from orders.models import Order, OrderItem
from users.models import User
from products.models import Product, Category
from cart.services import RedisCart


class OrderCreationTestCase(APITestCase):
    """Test suite for order creation from cart"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("orders")
        
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
        
        self.category = Category.objects.create(name="Electronics")
        self.product1 = Product.objects.create(
            name="Laptop",
            price=1000.00,
            stock=10,
            category=self.category
        )
        self.product2 = Product.objects.create(
            name="Mouse",
            price=25.00,
            stock=50,
            category=self.category
        )
        self.product3 = Product.objects.create(
            name="Keyboard",
            price=75.00,
            stock=0,  # Out of stock
            category=self.category
        )

    def tearDown(self):
        """Clean up Redis cart after each test"""
        cart = RedisCart(self.user)
        cart.clear()

    def authenticate(self, user=None):
        user = user or self.user
        self.client.force_authenticate(user=user)

    def add_to_cart(self, user, product_id, quantity):
        cart = RedisCart(user)
        cart.add(product_id, quantity)

    def test_create_order_success(self):
        self.authenticate()
        
        # Add items to cart
        self.add_to_cart(self.user, self.product1.id, 2)
        self.add_to_cart(self.user, self.product2.id, 3)
        
        # Create order
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertIn("items", response.data)
        self.assertEqual(len(response.data["items"]), 2)
        self.assertEqual(response.data["status"], "pending")
        
        # Verify order exists in database
        order = Order.objects.get(id=response.data["id"])
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.items.count(), 2)
        
        # Verify total price
        expected_total = (1000.00 * 2) + (25.00 * 3)
        self.assertEqual(float(response.data["total_price"]), expected_total)

    def test_create_order_stock_reduced(self):
        """Test that product stock is reduced after order creation"""
        self.authenticate()
        
        initial_stock = self.product1.stock
        order_quantity = 3
        
        # Add to cart and create order
        self.add_to_cart(self.user, self.product1.id, order_quantity)
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify stock was reduced
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, initial_stock - order_quantity)

    def test_create_order_cart_cleared(self):
        """Test that cart is cleared after successful order"""
        self.authenticate()
        
        # Add items to cart
        self.add_to_cart(self.user, self.product1.id, 1)
        cart = RedisCart(self.user)
        
        # Verify cart has items
        cart_data = cart.get_cart_details()
        self.assertEqual(len(cart_data["items"]), 1)
        
        # Create order
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify cart is now empty
        cart_data = cart.get_cart_details()
        self.assertEqual(len(cart_data["items"]), 0)

    def test_create_order_empty_cart(self):
        """Test that order creation fails with empty cart"""
        self.authenticate()
        
        # Try to create order with empty cart
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Your Cart is Empty", response.data)
        
        # Verify no order was created
        self.assertEqual(Order.objects.count(), 0)

    def test_create_order_insufficient_stock(self):
        """Test that order creation fails if product has insufficient stock"""
        self.authenticate()
        
        # Manually add to Redis bypassing cart validation
        cart = RedisCart(self.user)
        cart.redis.hset(cart.key, self.product1.id, self.product1.stock + 5)
        
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        # Verify no order was created
        self.assertEqual(Order.objects.count(), 0)
        
        # Verify stock was not reduced
        self.product1.refresh_from_db()
        self.assertEqual(self.product1.stock, 10)

    def test_create_order_product_out_of_stock(self):
        """Test order creation fails for out-of-stock products"""
        self.authenticate()
        
        # Add out-of-stock product to cart
        cart = RedisCart(self.user)
        # Manually add to Redis bypassing validation for testing
        cart.redis.hset(cart.key, self.product3.id, 1)
        
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_create_order_product_not_found(self):
        """Test order creation fails if product in cart doesn't exist"""
        self.authenticate()
        
        # Manually add non-existent product to cart
        cart = RedisCart(self.user)
        cart.redis.hset(cart.key, 99999, 1)
        
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Your Cart is Empty", response.data)

    def test_create_order_transaction_rollback(self):
        """Test that transaction rolls back on error (stock not reduced)"""
        self.authenticate()
        
        # Manually add to Redis bypassing cart validation
        # to test order creation transaction atomicity
        cart = RedisCart(self.user)
        cart.redis.hset(cart.key, self.product1.id, 2)
        # product2 has 50 in stock, try to order 100
        cart.redis.hset(cart.key, self.product2.id, 100)
        
        initial_stock1 = self.product1.stock
        initial_stock2 = self.product2.stock
        
        # Try to create order (should fail on product2 insufficient stock)
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("stock", str(response.data["error"]).lower())
        
        # Verify stock was NOT reduced for product1 (transaction rolled back)
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.stock, initial_stock1)
        self.assertEqual(self.product2.stock, initial_stock2)
        
        # Verify no order items were created
        self.assertEqual(OrderItem.objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)

    def test_create_order_correct_prices_saved(self):
        """Test that order items save the current product price"""
        self.authenticate()
        
        self.add_to_cart(self.user, self.product1.id, 1)
        
        # Create order
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Get order item
        order = Order.objects.get(id=response.data["id"])
        order_item = order.items.first()
        
        # Verify price was saved
        self.assertEqual(order_item.price, self.product1.price)
        
        # Change product price
        self.product1.price = 1500.00
        self.product1.save()
        
        # Verify order item still has original price
        order_item.refresh_from_db()
        self.assertEqual(float(order_item.price), 1000.00)

    def test_create_order_unauthenticated(self):
        """Test that unauthenticated users cannot create orders"""
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


