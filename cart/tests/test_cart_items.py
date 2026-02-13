from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from users.models import User
from products.models import Product, Category
from cart.services import RedisCart


class CartItemsTestCase(APITestCase):
    """Test suite for CartItemsView (Add/Update/Remove items)"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.add_url = reverse("cart-items")
        
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
        self.product_out_of_stock = Product.objects.create(
            name="Keyboard",
            price=75.00,
            stock=0,
            category=self.category
        )

    def tearDown(self):
        """Clean up Redis cart after each test"""
        cart = RedisCart(self.user)
        cart.clear()

    def authenticate(self):
        """Authenticate user"""
        self.client.force_authenticate(user=self.user)

    def get_update_url(self, product_id):
        """Get URL for updating/deleting a cart item"""
        return reverse("cart-item-detail", kwargs={"pk": product_id})

    # ========== ADD TO CART TESTS ==========

    def test_add_item_to_cart(self):
        """Test successfully adding item to cart"""
        self.authenticate()
        
        data = {"product_id": self.product1.id, "quantity": 2}
        response = self.client.post(self.add_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        
        # Verify item in cart
        cart = RedisCart(self.user)
        cart_data = cart.get_cart_details()
        self.assertEqual(len(cart_data["items"]), 1)

    def test_add_item_unauthenticated(self):
        """Test unauthenticated user cannot add to cart"""
        data = {"product_id": self.product1.id, "quantity": 2}
        response = self.client.post(self.add_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_add_item_invalid_product(self):
        """Test adding non-existent product fails"""
        self.authenticate()
        
        data = {"product_id": 99999, "quantity": 1}
        response = self.client.post(self.add_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("product_id", response.data)  # Serializer validation error

    def test_add_item_default_quantity(self):
        """Test adding item without quantity uses default of 1"""
        self.authenticate()
        
        data = {"product_id": self.product1.id}
        response = self.client.post(self.add_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify quantity is 1
        cart = RedisCart(self.user)
        cart_data = cart.get_cart_details()
        self.assertEqual(cart_data["items"][0]["quantity"], 1)

    def test_add_item_exceeds_stock(self):
        """Test cannot add more than available stock"""
        self.authenticate()
        
        data = {"product_id": self.product1.id, "quantity": 15}  # Stock is 10
        response = self.client.post(self.add_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("stock", str(response.data["error"]).lower())

    def test_add_item_zero_quantity(self):
        """Test cannot add item with zero quantity"""
        self.authenticate()
        
        data = {"product_id": self.product1.id, "quantity": 0}
        response = self.client.post(self.add_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_item_negative_quantity(self):
        """Test cannot add item with negative quantity"""
        self.authenticate()
        
        data = {"product_id": self.product1.id, "quantity": -5}
        response = self.client.post(self.add_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_same_item_twice(self):
        """Test adding same item twice increments quantity"""
        self.authenticate()
        
        # Add item first time
        data = {"product_id": self.product1.id, "quantity": 2}
        self.client.post(self.add_url, data)
        
        # Add same item again
        data = {"product_id": self.product1.id, "quantity": 3}
        response = self.client.post(self.add_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify quantity is cumulative (2 + 3 = 5)
        cart = RedisCart(self.user)
        cart_data = cart.get_cart_details()
        self.assertEqual(cart_data["items"][0]["quantity"], 5)

    def test_add_cumulative_exceeds_stock(self):
        """Test cannot add if current + new quantity exceeds stock"""
        self.authenticate()
        
        # Add 6 items
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 6)
        
        # Try to add 5 more (total would be 11, stock is 10)
        data = {"product_id": self.product1.id, "quantity": 5}
        response = self.client.post(self.add_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_add_out_of_stock_product(self):
        """Test cannot add out-of-stock product"""
        self.authenticate()
        
        data = {"product_id": self.product_out_of_stock.id, "quantity": 1}
        response = self.client.post(self.add_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_add_missing_product_id(self):
        """Test adding without product_id fails"""
        self.authenticate()
        
        data = {"quantity": 2}
        response = self.client.post(self.add_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ========== UPDATE CART ITEM TESTS ==========

    def test_update_item_quantity(self):
        """Test successfully updating item quantity"""
        self.authenticate()
        
        # Add item first
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 2)
        
        # Update quantity
        url = self.get_update_url(self.product1.id)
        data = {"quantity": 5}
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify quantity updated
        cart_data = cart.get_cart_details()
        self.assertEqual(cart_data["items"][0]["quantity"], 5)

    def test_update_item_unauthenticated(self):
        """Test unauthenticated user cannot update cart"""
        url = self.get_update_url(self.product1.id)
        data = {"quantity": 5}
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_item_exceeds_stock(self):
        """Test cannot update quantity to exceed stock"""
        self.authenticate()
        
        # Add item
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 2)
        
        # Try to update to exceed stock
        url = self.get_update_url(self.product1.id)
        data = {"quantity": 15}  # Stock is 10
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_update_item_to_zero_removes(self):
        """Test updating quantity to 0 removes item"""
        self.authenticate()
        
        # Add item
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 2)
        
        # Update to 0
        url = self.get_update_url(self.product1.id)
        data = {"quantity": 0}
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("removed", response.data["message"].lower())
        
        # Verify item removed
        cart_data = cart.get_cart_details()
        self.assertEqual(len(cart_data["items"]), 0)

    def test_update_nonexistent_product(self):
        """Test updating non-existent product fails"""
        self.authenticate()
        
        url = self.get_update_url(99999)
        data = {"quantity": 5}
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)

    def test_update_missing_quantity(self):
        """Test updating without quantity field fails"""
        self.authenticate()
        
        url = self.get_update_url(self.product1.id)
        response = self.client.put(url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_negative_quantity(self):
        """Test cannot update to negative quantity"""
        self.authenticate()
        
        url = self.get_update_url(self.product1.id)
        data = {"quantity": -5}
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ========== REMOVE FROM CART TESTS ==========

    def test_remove_item_from_cart(self):
        """Test successfully removing item from cart"""
        self.authenticate()
        
        # Add item
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 2)
        
        # Remove item
        url = self.get_update_url(self.product1.id)
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify item removed
        cart_data = cart.get_cart_details()
        self.assertEqual(len(cart_data["items"]), 0)

    def test_remove_item_unauthenticated(self):
        """Test unauthenticated user cannot remove from cart"""
        url = self.get_update_url(self.product1.id)
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_remove_nonexistent_item(self):
        """Test removing non-existent item is idempotent"""
        self.authenticate()
        
        url = self.get_update_url(self.product1.id)
        response = self.client.delete(url)
        
        # Should succeed (idempotent)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_remove_item_from_cart_with_multiple_items(self):
        """Test removing one item leaves others intact"""
        self.authenticate()
        
        # Add multiple items
        cart = RedisCart(self.user)
        cart.add(self.product1.id, 2)
        cart.add(self.product2.id, 3)
        
        # Remove one item
        url = self.get_update_url(self.product1.id)
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify only product2 remains
        cart_data = cart.get_cart_details()
        self.assertEqual(len(cart_data["items"]), 1)
        self.assertEqual(cart_data["items"][0]["product_id"], self.product2.id)
