from django_redis import get_redis_connection
from products.models import Product  
from django.core.exceptions import ValidationError

class RedisCart:
    def __init__(self, user):
        self.user = user
        self.key = f"cart:user_{user.id}"
        self.redis = get_redis_connection("default")

    def _check_stock(self, product_id, quantity):
        """Helper method to validate stock"""
        
        product = Product.objects.get(id=product_id)
        if quantity > product.stock:
            raise ValidationError(f"Not enough stock. Only {product.stock} available.")
        return product
    
    def add(self, product_id, quantity=1):
        product = self._check_stock(product_id, quantity)
        current_qty = int(self.redis.hget(self.key, product_id) or 0)
        new_qty = current_qty + quantity
        
        if new_qty > product.stock:
            raise ValidationError(f"Only {product.stock} units available")
        
        self.redis.hincrby(self.key, product_id, quantity)
        self.redis.expire(self.key, 60 * 60 * 24 * 7) # 1 Week

    def remove(self, product_id):
        self.redis.hdel(self.key, product_id)

    def update(self, product_id, quantity):
        if quantity > 0:
            product = self._check_stock(product_id, quantity)
            self.redis.hset(self.key, product_id, quantity)
            self.redis.expire(self.key, 60 * 60 * 24 * 7) # 1 Week
        else:
            self.remove(product_id)

    def get_cart_details(self):
        cart_data = self.redis.hgetall(self.key)
        
        if not cart_data:
            return {"items": [], "total_price": 0, "count": 0}

        cart_items = {int(k): int(v) for k, v in cart_data.items()}
        
        product_ids = cart_items.keys()
        products = Product.objects.filter(id__in=product_ids)

        results = []
        total_price = 0
        
        for product in products:
            quantity = cart_items[product.id]
            subtotal = product.price * quantity
            total_price += subtotal
            
            results.append({
                "product_id": product.id,
                "name": product.name,
                "price": float(product.price),
                "image": product.image.url if product.image else None,
                "quantity": quantity,
                "subtotal": float(subtotal)
            })

        return {
            "items": results,
            "total_price": float(total_price),
            "count": len(results)
        }

    def clear(self):
        self.redis.delete(self.key)