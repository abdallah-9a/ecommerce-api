from django.test import TestCase
from products.models import Product, Category


class ModelsTest(TestCase):
    def setUp(self):
        category = Category.objects.create(name="name")
        self.product = Product.objects.create(
            name="Café C++ Primer #1 — Version 2.0_beta-ALPHA@Email/Path&Rock, Roll!!!",  # cover almost all cases
            price=100,
            category=category,
        )

    def test_product_model_slug(self):
        # Django's slugify strips +, #, ., @, /, &, !, etc.
        self.assertEqual(
            self.product.slug,
            "cafe-c-primer-1-version-20_beta-alphaemailpathrock-roll",
        )
