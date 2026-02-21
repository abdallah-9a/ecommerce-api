import stripe
from decimal import Decimal
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from orders.models import Order
from .models import Payment
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse


stripe.api_key = settings.STRIPE_SECRET_KEY

class CreatePaymentIntentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        order_id = request.data.get('order_id')
        
        order = get_object_or_404(Order, id=order_id, user=request.user)

        amount = int(order.total_price() * 100) # cents for Stripe

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd', 
                automatic_payment_methods={
                    'enabled': True,
                },
                metadata={
                    'order_id': order.id
                }
            )

            Payment.objects.create(
                order=order,
                stripe_payment_intent_id=intent['id'],
                amount=Decimal(amount) / 100,
                currency='usd',
                status='pending',
            )

            return Response({
                'client_secret': intent['client_secret']
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)
    
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=status.HTTP_400_BAD_REQUEST)


    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        intent_id = payment_intent['id']
        order_id = payment_intent['metadata'].get('order_id')

        if order_id:
            try:
                order = Order.objects.get(id=order_id)
                order.status = 'paid'
                order.save()
            except Order.DoesNotExist:
                return HttpResponse(status=status.HTTP_400_BAD_REQUEST)

            Payment.objects.filter(
                stripe_payment_intent_id=intent_id
            ).update(status='succeeded')

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        intent_id = payment_intent['id']

        Payment.objects.filter(
            stripe_payment_intent_id=intent_id
        ).update(status='failed')

    elif event['type'] == 'payment_intent.canceled':
        payment_intent = event['data']['object']
        intent_id = payment_intent['id']

        Payment.objects.filter(
            stripe_payment_intent_id=intent_id
        ).update(status='canceled')

    return HttpResponse(status=status.HTTP_200_OK)