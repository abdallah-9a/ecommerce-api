# Django E-commerce REST API

A comprehensive RESTful E-commerce API built with Django Rest Framework, featuring user authentication, product management, shopping cart functionality, order processing, and more.

## Project Overview

This Django-based e-commerce API provides a robust backend solution for online shopping applications. It includes user authentication with JWT tokens, product and category management, shopping cart functionality, and order processing capabilities.

### Key Features

- **User Authentication**: JWT-based authentication system with token refresh, login, logout, and password reset functionality
- **User Management**: User registration, profile management, and admin-only user operations
- **Product Catalog**: Product listing with categories, search, and filtering capabilities
- **Shopping Cart**: Cart management with add, update, and remove item operations
- **Order Processing**: Order creation, status tracking, and cancellation
- **Admin Controls**: Admin-specific endpoints for product, category, and order management
- **Pagination**: Custom pagination for list views
- **Permissions**: Role-based permissions (admin vs regular users)

## API Endpoints

### Authentication & User Management

| Endpoint                                   | Method | Description                        | Access        |
| ------------------------------------------ | ------ | ---------------------------------- | ------------- |
| `/api/users/register/`                     | POST   | Register a new user                | Public        |
| `/api/users/login/`                        | POST   | Login and get JWT tokens           | Public        |
| `/api/users/logout/`                       | POST   | Logout and blacklist refresh token | Authenticated |
| `/api/users/me/`                           | GET    | Get user profile data              | Authenticated |
| `/api/users/me/update/`                    | PUT    | Update user profile                | Authenticated |
| `/api/users/`                              | GET    | List all users                     | Admin         |
| `/api/users/<id>/`                         | GET    | Get specific user details          | Admin         |
| `/api/users/change-password/`              | POST   | Change password                    | Authenticated |
| `/api/users/send-reset-password-email/`    | POST   | Send password reset email          | Public        |
| `/api/users/reset-password/<uid>/<token>/` | POST   | Reset password with token          | Public        |

### Products & Categories

| Endpoint                   | Method | Description                         | Access |
| -------------------------- | ------ | ----------------------------------- | ------ |
| `/api/v1/products/`        | GET    | List all products with pagination   | Public |
| `/api/v1/products/`        | POST   | Create a new product                | Admin  |
| `/api/v1/products/<id>/`   | GET    | Get product details                 | Public |
| `/api/v1/products/<id>/`   | PUT    | Update a product                    | Admin  |
| `/api/v1/products/<id>/`   | DELETE | Delete a product                    | Admin  |
| `/api/v1/categories/`      | GET    | List all categories with pagination | Public |
| `/api/v1/categories/`      | POST   | Create a new category               | Admin  |
| `/api/v1/categories/<id>/` | GET    | Get category details                | Public |
| `/api/v1/categories/<id>/` | PUT    | Update a category                   | Admin  |
| `/api/v1/categories/<id>/` | DELETE | Delete a category                   | Admin  |

### Shopping Cart

| Endpoint                   | Method | Description               | Access        |
| -------------------------- | ------ | ------------------------- | ------------- |
| `/api/v1/cart/`            | GET    | View user's shopping cart | Authenticated |
| `/api/v1/cart/add/`        | POST   | Add product to cart       | Authenticated |
| `/api/v1/cart/items/<id>/` | GET    | View specific cart item   | Authenticated |
| `/api/v1/cart/items/<id>/` | PUT    | Update cart item quantity | Authenticated |
| `/api/v1/cart/items/<id>/` | DELETE | Remove item from cart     | Authenticated |

### Orders

| Endpoint                      | Method | Description                      | Access        |
| ----------------------------- | ------ | -------------------------------- | ------------- |
| `/api/v1/orders/`             | GET    | List user orders with pagination | Authenticated |
| `/api/v1/orders/`             | POST   | Create new order from cart items | Authenticated |
| `/api/v1/orders/<id>/`        | GET    | Get order details                | Authenticated |
| `/api/v1/orders/<id>/status/` | PUT    | Update order status              | Admin         |
| `/api/v1/orders/<id>/cancel/` | PUT    | Cancel an order                  | Authenticated |

### Installation

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/django-ecommerce-rest-api.git
   cd django-ecommerce-rest-api
   ```

2. Create and activate a virtual environment:

   ```
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   Create a `.env` file in the project root with:

   ```
   SECRET_KEY=your_secret_key
   EMAIL_USER=your_email@example.com
   EMAIL_PASS=your_email_password
   ```

5. Run migrations:

   ```
   python manage.py migrate
   ```

6. Create a superuser:

   ```
   python manage.py createsuperuser
   ```

7. Run the development server:
   ```
   python manage.py runserver
   ```
