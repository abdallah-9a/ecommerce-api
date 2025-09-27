from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from .models import User

# Create your tests here.


class UsersAPITestCase(APITestCase):

    USER_EMAIL = "user@gmail.com"
    USER_PASSWORD = "user1234"
    ADMIN_EMAIL = "admin@gmail.com"
    ADMIN_PASSWORD = "admin1234"

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="user", email=self.USER_EMAIL, password=self.USER_PASSWORD
        )
        self.admin = User.objects.create_superuser(
            username="Admin", email=self.ADMIN_EMAIL, password=self.ADMIN_PASSWORD
        )

    def authenticate_user(self, email=None, password=None):
        """Log in a user and set Authorization header; returns tokens dict."""
        email = email or self.USER_EMAIL
        password = password or self.USER_PASSWORD
        response = self.client.post(
            reverse("login"), {"email": email, "password": password}
        )
        self.assertEqual(
            response.status_code, status.HTTP_200_OK, msg="Login failed in test helper"
        )
        tokens = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        return tokens

    def authenticate_admin(self):
        """Log in as admin and set Authorization header; returns tokens dict."""
        return self.authenticate_user(self.ADMIN_EMAIL, self.ADMIN_PASSWORD)

    def test_registration(self):
        data = {
            "email": "test@gmail.com",
            "username": "Test",
            "password": "12345678",
            "password2": "12345678",
        }
        response = self.client.post(reverse("register"), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_login(self):
        tokens = self.authenticate_user()
        self.assertIn("access", tokens)
        self.assertIn("refresh", tokens)

    def test_logout(self):
        tokens = self.authenticate_user()
        response = self.client.post(reverse("logout"), {"refresh": tokens["refresh"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile(self):
        self.authenticate_user()
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_profile(self):
        self.authenticate_user()
        data = {"first_name": "user", "username": "User1"}
        response = self.client.patch(reverse("update-profile"), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_change_password(self):
        self.authenticate_user()
        data = {
            "old_password": self.USER_PASSWORD,
            "password": "User1234",
            "password2": "User1234",
        }
        response = self.client.post(reverse("change-password"), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_list(self):
        self.authenticate_admin()
        response = self.client.get(reverse("users-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_detail(self):
        self.authenticate_admin()
        response = self.client.get(reverse("user-detail", kwargs={"pk": self.user.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
