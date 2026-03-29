from celery import shared_task
from django.db import transaction
from .models import Order, Payment

@shared_task(name="process_stripe_webhook_task")
def process_stripe_webhook_task(event):
    event_type = event['type']
    data_object = event['data']['object']
    intent_id = data_object['id']

    if event_type == 'payment_intent.succeeded':
        order_id = data_object['metadata'].get('order_id')
        if order_id:
            try:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(id=order_id)
                    if order.can_transition_to('paid'):
                        order.transition_to('paid')
            except Order.DoesNotExist:
                return f"Order {order_id} not found"

        Payment.objects.filter(stripe_payment_intent_id=intent_id).update(status='succeeded')

    elif event_type in ['payment_intent.payment_failed', 'payment_intent.canceled']:
        new_status = 'failed' if event_type == 'payment_intent.payment_failed' else 'canceled'
        Payment.objects.filter(stripe_payment_intent_id=intent_id).update(status=new_status)

    return f"Processed {event_type} for intent {intent_id}"