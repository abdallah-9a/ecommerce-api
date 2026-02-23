from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from orders.models import Order, OrderItem
from payments.models import Payment
from users.models import User
from products.models import Product, Category


class CreatePaymentIntentTestCase(APITestCase):
    """Test suite for CreatePaymentIntentView"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("create-payment-intent")

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123",
        )

        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            stock=10,
            category=self.category,
        )

        self.order = Order.objects.create(user=self.user, status="pending")
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            price=self.product.price,
        )

    @patch("payments.views.stripe.PaymentIntent.create")
    def test_create_payment_intent_success(self, mock_create):
        mock_create.return_value = {
            "id": "pi_test_123",
            "client_secret": "pi_test_123_secret_abc",
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"order_id": self.order.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("client_secret", response.data)
        self.assertEqual(response.data["client_secret"], "pi_test_123_secret_abc")

        # Verify Payment record was created
        payment = Payment.objects.get(stripe_payment_intent_id="pi_test_123")
        self.assertEqual(payment.order, self.order)
        self.assertEqual(payment.amount, Decimal("2000.00"))
        self.assertEqual(payment.currency, "usd")
        self.assertEqual(payment.status, "pending")

    def test_create_payment_intent_unauthenticated(self):
        response = self.client.post(self.url, {"order_id": self.order.id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_payment_intent_other_users_order(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(self.url, {"order_id": self.order.id})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_payment_intent_nonexistent_order(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {"order_id": 99999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class StripeWebhookTestCase(APITestCase):
    """Test suite for stripe_webhook view"""

    def setUp(self):
        self.url = reverse("stripe-webhook")

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

        self.category = Category.objects.create(name="Electronics")
        self.product = Product.objects.create(
            name="Laptop",
            price=Decimal("1000.00"),
            stock=10,
            category=self.category,
        )

        self.order = Order.objects.create(user=self.user, status="pending")
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            price=self.product.price,
        )

        self.payment = Payment.objects.create(
            order=self.order,
            stripe_payment_intent_id="pi_test_123",
            amount=Decimal("1000.00"),
            currency="usd",
            status="pending",
        )

    def _build_event(self, event_type, intent_id, order_id):
        return {
            "type": event_type,
            "data": {
                "object": {
                    "id": intent_id,
                    "metadata": {"order_id": str(order_id)},
                }
            },
        }

    @patch("payments.views.stripe.Webhook.construct_event")
    def test_payment_succeeded(self, mock_construct):
        event = self._build_event(
            "payment_intent.succeeded", "pi_test_123", self.order.id
        )
        mock_construct.return_value = event

        response = self.client.post(
            self.url,
            data=b"payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "paid")

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "succeeded")

    @patch("payments.views.stripe.Webhook.construct_event")
    def test_invalid_signature(self, mock_construct):
        import stripe

        mock_construct.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", "sig_header"
        )

        response = self.client.post(
            self.url,
            data=b"payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="bad_sig",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("payments.views.stripe.Webhook.construct_event")
    def test_nonexistent_order(self, mock_construct):
        event = self._build_event(
            "payment_intent.succeeded", "pi_test_123", 99999
        )
        mock_construct.return_value = event

        response = self.client.post(
            self.url,
            data=b"payload",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )

        # View returns 400 for nonexistent order
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Payment record should NOT be updated to succeeded
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, "pending")
