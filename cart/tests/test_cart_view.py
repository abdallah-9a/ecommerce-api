from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from users.models import User
from products.models import Product, Category
from cart.services import RedisCart


class CartViewTestCase(APITestCase):
    """Test suite for CartView (GET/DELETE cart)"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.cart_url = reverse("cart")
        
        # Create user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        # Create category and products
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

    def tearDown(self):
        """Clean up Redis cart after each test"""
        cart = RedisCart(self.user)
        cart.clear()

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def test_get_cart_authenticated(self):
        self.authenticate()
        
        response = self.client.get(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("items", response.data)
        self.assertIn("total_price", response.data)
        self.assertIn("count", response.data)

    def test_get_cart_unauthenticated(self):
        response = self.client.get(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_empty_cart(self):
        self.authenticate()
        
        response = self.client.get(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["total_price"], 0)
        self.assertEqual(response.data["count"], 0)

    def test_get_cart_with_items(self):
        self.authenticate()
        
        # Add items to cart
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 2)
        cart.add(self.product2.id, 3)
        
        response = self.client.get(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 2)
        self.assertEqual(response.data["count"], 2)

    def test_get_cart_calculates_total_price(self):
        """Test cart calculates total price correctly"""
        self.authenticate()
        
        # Add items to cart
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 2)  # 2 * 1000 = 2000
        cart.add(self.product2.id, 3)  # 3 * 25 = 75
        
        response = self.client.get(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_total = (2 * 1000.00) + (3 * 25.00)
        self.assertEqual(float(response.data["total_price"]), expected_total)

    def test_get_cart_includes_item_details(self):
        """Test cart items include all required fields"""
        self.authenticate()
        
        # Add item to cart
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 2)
        
        response = self.client.get(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data["items"][0]
        
        # Check all required fields
        self.assertIn("product_id", item)
        self.assertIn("name", item)
        self.assertIn("price", item)
        self.assertIn("quantity", item)
        self.assertIn("subtotal", item)
        self.assertEqual(item["product_id"], self.product1.id)
        self.assertEqual(item["name"], "Laptop")
        self.assertEqual(item["quantity"], 2)

    def test_get_cart_calculates_subtotals(self):
        """Test cart calculates item subtotals correctly"""
        self.authenticate()
        
        # Add item to cart
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 3)
        
        response = self.client.get(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data["items"][0]
        
        expected_subtotal = 3 * 1000.00
        self.assertEqual(float(item["subtotal"]), expected_subtotal)

    def test_clear_cart_authenticated(self):
        """Test authenticated user can clear cart"""
        self.authenticate()
        
        # Add items to cart
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 2)
        
        response = self.client.delete(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify cart is empty
        cart_data = cart.get_cart_details()
        self.assertEqual(len(cart_data["items"]), 0)

    def test_clear_cart_unauthenticated(self):
        """Test unauthenticated users cannot clear cart"""
        response = self.client.delete(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_cart_after_clear(self):
        """Test getting cart after clearing returns empty cart"""
        self.authenticate()
        
        # Add items and clear
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 2)
        self.client.delete(self.cart_url)
        
        # Get cart
        response = self.client.get(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertEqual(response.data["total_price"], 0)

    def test_cart_ignores_deleted_products(self):
        """Test cart filters out deleted products"""
        self.authenticate()
        
        # Add items to cart
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 2)
        cart.add(self.product2.id, 1)
        
        # Delete one product
        self.product1.delete()
        
        # Get cart
        response = self.client.get(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only product2 should remain
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["product_id"], self.product2.id)

    def test_cart_shows_current_prices(self):
        """Test cart shows current product prices (not price when added)"""
        self.authenticate()
        
        # Add item to cart
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 1)
        
        # Change product price
        self.product1.price = 1200.00
        self.product1.save()
        
        # Get cart
        response = self.client.get(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = response.data["items"][0]
        # Should show updated price
        self.assertEqual(float(item["price"]), 1200.00)

    def test_clear_empty_cart(self):
        """Test clearing an already empty cart"""
        self.authenticate()
        
        response = self.client.delete(self.cart_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
