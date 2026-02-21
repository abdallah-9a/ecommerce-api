from django.db import models
from orders.models import Order


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("succeeded", "Succeeded"),
        ("failed", "Failed"),
        ("canceled", "Canceled"),
    ]

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="payments"
    )
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="usd")
    status = models.CharField(
        choices=STATUS_CHOICES, max_length=10, default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.stripe_payment_intent_id} for Order #{self.order_id} ({self.status})"
