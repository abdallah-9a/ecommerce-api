import stripe
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from orders.models import Order
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
        
        order_id = payment_intent['metadata'].get('order_id')

        if order_id:
            try:
                order = Order.objects.get(id=order_id)
                order.status = 'paid'
                order.save()

            except Order.DoesNotExist:
                raise ValueError("Order not found for payment intent")

    return HttpResponse(status=status.HTTP_200_OK)

    #TODO