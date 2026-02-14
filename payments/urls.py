from django.urls import path
from .views import CreatePaymentIntentView, stripe_webhook
urlpatterns = [
        path("create-payment-intent/", CreatePaymentIntentView.as_view(), name="create-payment-intent"),
        path('webhook/', stripe_webhook, name='stripe-webhook'),
]