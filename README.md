# E-commerce API — Django REST, Redis Cart, Stripe Payments

Production-minded E-commerce REST API built with **Django** and **Django REST Framework (DRF)**, featuring **JWT authentication**, a **Redis-backed cart**, **order processing with a robust state machine**, and **Stripe PaymentIntent** integration.

Designed to demonstrate real backend engineering concerns: **async work offloading**, **data integrity**, **concurrency safety**, and **reliable webhook ingestion**.

---

## Key Features

- **JWT Authentication** (SimpleJWT): register/login/logout, profile, password change, password reset
- **Product & Category management** with pagination and filtering
- **Redis-backed cart** (fast reads/writes, expiration, stock checks)
- **Order processing** from cart → order items + stock decrement
- **Robust order state machine** preventing invalid transitions (e.g., `canceled → paid`)
- **Stripe integration**: create PaymentIntent + webhook updates for payments
- **Async processing with Celery + Redis** for non-blocking tasks (email + webhook processing; extensible to invoice/PDF generation)
- **Concurrency control**: database row-level locking using `select_for_update()` during critical sections

---

## Quickstart (Local Development)

### Prerequisites

- Python 3.10+
- Redis (used for cart storage and Celery broker/result backend)
- Stripe account (for PaymentIntents + webhook signature verification)

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables

Create a `.env` file at the project root:

```env
# Django
SECRET_KEY=change-me

# Email (used by password reset task)
EMAIL_USER=your_email@example.com
EMAIL_PASS=your_email_password
FROM_EMAIL=your_email@example.com

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Celery (optional overrides)
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/3
```

### 4) Run migrations

```bash
python manage.py migrate
```

### 5) Create an admin user (optional)

```bash
python manage.py createsuperuser
```

### 6) Start Redis

If you already have Redis installed locally:

```bash
redis-server
```

By default, this project uses separate Redis logical databases:

- `redis://127.0.0.1:6379/2` for cache/cart
- `redis://127.0.0.1:6379/0` for the Celery broker
- `redis://127.0.0.1:6379/3` for the Celery result backend

Or via Docker:

```bash
docker run --rm -p 6379:6379 redis:7-alpine
```

### 7) Start Celery worker

In a separate terminal:

```bash
celery -A ecommerce worker -l info
```

### 8) Run the Django development server

```bash
python manage.py runserver
```

---

## Stripe Webhooks (Local)

This project validates webhook signatures using `STRIPE_WEBHOOK_SECRET` and **queues processing** to Celery.

Recommended local workflow using the Stripe CLI:

```bash
stripe listen --forward-to http://127.0.0.1:8000/api/v1/payments/webhook/
```

Then copy the printed webhook secret (`whsec_...`) into your `.env`.

---

## API Endpoints (Current Routes)

Base URL prefix: `/api/v1/`

### Auth & Users

- `POST /api/v1/users/register/`
- `POST /api/v1/users/login/`
- `POST /api/v1/users/logout/`
- `GET  /api/v1/users/me/`
- `PUT  /api/v1/users/me/update/`
- `POST /api/v1/users/change-password/`
- `POST /api/v1/users/send-reset-password-email/`
- `POST /api/v1/users/reset-password/<uid>/<token>/`
- `GET  /api/v1/users/` (admin)
- `GET  /api/v1/users/<id>/` (admin)

### Products & Categories

- `GET/POST /api/v1/products/`
- `GET/PUT/DELETE /api/v1/products/<id>/`
- `GET/POST /api/v1/categories/`
- `GET/PUT/DELETE /api/v1/categories/<id>/`

### Cart (Redis-backed)

- `GET  /api/v1/cart/`
- `DELETE /api/v1/cart/` (clear cart)
- `POST /api/v1/cart/items/` (add item)
- `PUT  /api/v1/cart/items/<product_id>/` (update quantity)
- `DELETE /api/v1/cart/items/<product_id>/` (remove)

### Orders

- `GET/POST /api/v1/orders/`
- `GET /api/v1/orders/<id>/`
- `PUT /api/v1/orders/<id>/status/` (admin)
- `PUT /api/v1/orders/<id>/cancel/`

### Payments (Stripe)

- `POST /api/v1/payments/create-payment-intent/`
- `POST /api/v1/payments/webhook/` (Stripe)

---

## Authentication (JWT)

After `login`/`register`, include the access token:

```http
Authorization: Bearer <access_token>
```

---

## API Documentation (Swagger / Redoc)

OpenAPI schema and interactive documentation are available via **drf-spectacular**:

- OpenAPI schema: `/api/schema/`
- Swagger UI: `/api/docs/swagger/`
- Redoc: `/api/docs/redoc/`

---

## Design Patterns Used

- **Service Layer:** business logic encapsulation (e.g., Redis cart operations in a dedicated service)
- **State Machine:** order status transitions are centrally enforced on the model
- **Async Workers:** Celery tasks for background work (email + Stripe webhook processing)

---

## Running Tests

```bash
python manage.py test
```

---

## Future Improvements

- **PostgreSQL migration** for production-grade transactions/locking and better scalability
- **Dockerization** (Django + Redis + Celery) for reproducible local/prod environments
- **CI/CD pipeline** (linting, unit tests, build, deploy)
- **Idempotency for webhooks** (store processed event IDs) for extra safety under retries

---

## Tech Stack

- Django, Django REST Framework
- Celery + Redis
- SQLite (development)
- Stripe API

