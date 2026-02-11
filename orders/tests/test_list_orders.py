from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from orders.models import Order, OrderItem
from users.models import User
from products.models import Product, Category


class OrderListTestCase(APITestCase):
    """Test suite for listing orders"""

    def setUp(self):
        self.client = APIClient()
        self.list_url = reverse("orders")
        
        # Create users
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
        
        # Create category and products
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            name="Laptop",
            price=1000.00,
            stock=100,
            category=self.category
        )
        
        # Create orders for user
        self.order1 = Order.objects.create(user=self.user, status="pending")
        OrderItem.objects.create(
            order=self.order1,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        self.order2 = Order.objects.create(user=self.user, status="paid")
        OrderItem.objects.create(
            order=self.order2,
            product=self.product,
            quantity=2,
            price=self.product.price
        )
        
        self.order3 = Order.objects.create(user=self.user, status="shipped")
        OrderItem.objects.create(
            order=self.order3,
            product=self.product,
            quantity=1,
            price=self.product.price
        )
        
        # Create order for other user
        self.other_order = Order.objects.create(user=self.other_user, status="pending")
        OrderItem.objects.create(
            order=self.other_order,
            product=self.product,
            quantity=1,
            price=self.product.price
        )

    def authenticate(self, user=None):
        """Authenticate user"""
        user = user or self.user
        self.client.force_authenticate(user=user)

    def test_list_orders_success(self):
        """Test authenticated user can list their orders"""
        self.authenticate()
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 3)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify all returned orders belong to user
        for order in response.data["results"]:
            self.assertEqual(order["user"], self.user.email)

    def test_list_orders_unauthenticated(self):
        """Test unauthenticated users cannot list orders"""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_orders_includes_items(self):
        """Test that order list includes order items"""
        self.authenticate()
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check first order has items
        first_order = response.data["results"][0]
        self.assertIn("items", first_order)
        self.assertGreater(len(first_order["items"]), 0)

    def test_list_orders_includes_total_price(self):
        """Test that order list includes total price"""
        self.authenticate()        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check first order has total_price
        first_order = response.data["results"][0]
        self.assertIn("total_price", first_order)
        self.assertIsNotNone(first_order["total_price"])

    def test_list_orders_pagination(self):
        """Test order list is paginated"""
        self.authenticate()
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check pagination fields
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)

    def test_list_orders_filter_by_status_pending(self):
        """Test filtering orders by status 'pending'"""
        self.authenticate()
        
        response = self.client.get(self.list_url, {"search": "pending"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only return pending orders
        for order in response.data["results"]:
            self.assertEqual(order["status"], "pending")

    def test_list_orders_filter_by_status_paid(self):
        """Test filtering orders by status 'paid'"""
        self.authenticate()
        
        response = self.client.get(self.list_url, {"search": "paid"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only return paid orders
        for order in response.data["results"]:
            self.assertEqual(order["status"], "paid")

    def test_list_orders_filter_by_status_shipped(self):
        """Test filtering orders by status 'shipped'"""
        self.authenticate()
        
        response = self.client.get(self.list_url, {"search": "shipped"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only return shipped orders
        for order in response.data["results"]:
            self.assertEqual(order["status"], "shipped")

    def test_list_orders_empty_list(self):
        """Test listing orders when user has no orders"""
        new_user = User.objects.create_user(
            username="newuser",
            email="new@example.com",
            password="testpass123"
        )
        self.authenticate(new_user)
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_list_orders_response_structure(self):
        """Test that order list response has correct structure"""
        self.authenticate()
        
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        order = response.data["results"][0]
        
        # Check required fields
        self.assertIn("id", order)
        self.assertIn("user", order)
        self.assertIn("status", order)
        self.assertIn("items", order)
        self.assertIn("total_price", order)


class OrderDetailTestCase(APITestCase):
    """Test suite for retrieving individual orders"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        
        # Create users
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
            stock=100,
            category=self.category
        )
        
        # Create order
        self.order = Order.objects.create(user=self.user, status="pending")
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=self.product.price
        )
        
        self.detail_url = reverse("order-detail", kwargs={"pk": self.order.pk})

    def authenticate(self, user=None):
        """Authenticate user"""
        user = user or self.user
        self.client.force_authenticate(user=user)

    def test_retrieve_order_success(self):
        """Test retrieving order details"""
        self.authenticate()
        
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.order.id)

    def test_retrieve_order_includes_items(self):
        """Test order detail includes order items"""
        self.authenticate()
        
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("items", response.data)
        self.assertEqual(len(response.data["items"]), 1)
        
        # Check item details
        item = response.data["items"][0]
        self.assertEqual(item["quantity"], 2)
        self.assertEqual(float(item["price"]), 1000.00)

    def test_retrieve_order_includes_total_price(self):
        """Test order detail includes calculated total price"""
        self.authenticate()
        
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("total_price", response.data)
        
        # Verify calculation
        expected_total = 1000.00 * 2
        self.assertEqual(float(response.data["total_price"]), expected_total)

    def test_retrieve_order_not_owner(self):
        """Test user cannot retrieve other users' orders"""
        self.authenticate(self.other_user)
        
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_order_unauthenticated(self):
        """Test unauthenticated users cannot retrieve orders"""
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_nonexistent_order(self):
        """Test retrieving non-existent order"""
        self.authenticate()
        
        url = reverse("order-detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_order_status(self):
        """Test order detail includes status"""
        self.authenticate()
        
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("status", response.data)
        self.assertEqual(response.data["status"], "pending")


    def test_retrieve_order_read_only(self):
        """Test that order detail endpoint is read-only"""
        self.authenticate()
        
        # Try POST
        response = self.client.post(self.detail_url, {})
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        
        # Try PUT
        response = self.client.put(self.detail_url, {})
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        
        # Try PATCH
        response = self.client.patch(self.detail_url, {})
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        
        # Try DELETE
        response = self.client.delete(self.detail_url)
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)


    def test_retrieve_order_response_structure(self):
        """Test order detail response has correct structure"""
        self.authenticate()
        
        response = self.client.get(self.detail_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check all required fields exist
        self.assertIn("id", response.data)
        self.assertIn("user", response.data)
        self.assertIn("status", response.data)
        self.assertIn("items", response.data)
        self.assertIn("total_price", response.data)
        
        # Check item structure
        item = response.data["items"][0]
        self.assertIn("id", item)
        self.assertIn("product", item)
        self.assertIn("quantity", item)
        self.assertIn("price", item)
