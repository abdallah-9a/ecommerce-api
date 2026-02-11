from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from orders.models import Order, OrderItem
from users.models import User
from products.models import Product, Category


class OrderStatusUpdateTestCase(APITestCase):
    """Test suite for admin order status updates"""

    def setUp(self):
        self.client = APIClient()
        
        # Create users
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123"
        )
        self.other_admin = User.objects.create_superuser(
            username="admin2",
            email="admin2@example.com",
            password="adminpass123"
        )
        
        # Create category and product
        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            name="Laptop",
            price=1000.00,
            stock=10,
            category=self.category
        )
        
        # Create order
        self.order = Order.objects.create(user=self.user, status="pending")
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=self.product.price
        )
        
        self.update_url = reverse("order-status", kwargs={"pk": self.order.pk})

    def authenticate_admin(self, admin=None):
        """Authenticate admin user"""
        admin = admin or self.admin
        self.client.force_authenticate(user=admin)

    def authenticate_user(self):
        """Authenticate regular user"""
        self.client.force_authenticate(user=self.user)

    def test_update_status_to_paid_success(self):
        """Test admin can update order status to 'paid'"""
        self.authenticate_admin()
        
        response = self.client.put(self.update_url, {"status": "paid"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify status was updated
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "paid")

    def test_update_status_to_shipped(self):
        """Test admin can update order status to 'shipped'"""
        self.authenticate_admin()
        
        response = self.client.put(self.update_url, {"status": "shipped"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "shipped")

    def test_update_status_to_delivered(self):
        """Test admin can update order status to 'delivered'"""
        self.authenticate_admin()
        
        response = self.client.put(self.update_url, {"status": "delivered"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "delivered")

    def test_update_status_to_canceled_fails(self):
        """Test admin cannot set status to 'canceled' (must use cancel endpoint)"""
        self.authenticate_admin()
        
        response = self.client.put(self.update_url, {"status": "canceled"})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify status was not changed
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")

    def test_update_status_regular_user_forbidden(self):
        """Test regular user cannot update order status"""
        self.authenticate_user()
        
        response = self.client.put(self.update_url, {"status": "paid"})
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify status was not changed
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")

    def test_update_status_unauthenticated(self):
        """Test unauthenticated users cannot update order status"""
        response = self.client.put(self.update_url, {"status": "paid"})
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_status_invalid_status(self):
        """Test updating to invalid status value"""
        self.authenticate_admin()
        
        response = self.client.put(self.update_url, {"status": "invalid_status"})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Verify status was not changed
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")

    def test_update_status_missing_status_field(self):
        """Test updating without providing status field"""
        self.authenticate_admin()
        
        response = self.client.put(self.update_url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_status_partial_update(self):
        """Test partial update (PATCH) of order status"""
        self.authenticate_admin()
        
        response = self.client.patch(self.update_url, {"status": "shipped"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "shipped")

    def test_update_nonexistent_order(self):
        """Test updating status of non-existent order"""
        self.authenticate_admin()
        
        url = reverse("order-status", kwargs={"pk": 99999})
        response = self.client.put(url, {"status": "paid"})
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


    def test_update_canceled_order_status(self):
        """Test admin can update a canceled order status"""
        self.authenticate_admin()
        
        self.order.status = "canceled"
        self.order.save()
        
        # Admin should be able to change status even for canceled orders
        response = self.client.put(self.update_url, {"status": "pending"})
        
        # This depends on your business logic - adjust if needed
        # Currently the code doesn't prevent this
        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_update_status_multiple_times(self):
        """Test updating status multiple times"""
        self.authenticate_admin()
        
        # Update to paid
        response = self.client.put(self.update_url, {"status": "paid"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Update to shipped
        response = self.client.put(self.update_url, {"status": "shipped"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Update to delivered
        response = self.client.put(self.update_url, {"status": "delivered"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify final status
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "delivered")

    def test_update_status_http_methods(self):
        """Test that only PUT/PATCH methods work"""
        self.authenticate_admin()
        
        # Test GET (should not update)
        response = self.client.get(self.update_url)
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        
        # Test POST (should not update)
        response = self.client.post(self.update_url, {"status": "paid"})
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        
        # Test DELETE (should not update)
        response = self.client.delete(self.update_url)
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify status unchanged
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")
