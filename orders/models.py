from django.db import models
from django.conf import settings
from rest_framework.exceptions import ValidationError
from products.models import Product

# Create your models here.


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("canceled", "Canceled"),
    ]

    VALID_STATUS_TRANSITIONS = {
        "pending": ["paid", "canceled"],
        "paid": ["shipped", "canceled"],
        "shipped": ["delivered"],
        "delivered": [],
        "canceled": [],
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )
    status = models.CharField(
        choices=STATUS_CHOICES, max_length=10, default="pending", db_index=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order #{self.id} for {self.user.username} ({self.status})"

    def total_price(self):
        return sum(item.price * item.quantity for item in self.items.all())

    def can_transition_to(self, new_status):
        if self.status == new_status:
            return True
        allowed = self.VALID_STATUS_TRANSITIONS.get(self.status, [])
        return new_status in allowed

    def transition_to(self, new_status):
        if not self.can_transition_to(new_status):
            allowed = self.VALID_STATUS_TRANSITIONS.get(self.status, [])
            raise ValidationError(
                f"Cannot transition from '{self.status}' to '{new_status}'. "
                f"Allowed transitions: {allowed}"
            )
        if self.status != new_status:
            self.status = new_status
            self.save(update_fields=["status", "updated_at"])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="order_items"
    )
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product} x {self.quantity} (order #{self.order.id})"
