import os

import stripe
from django.conf import settings

# Инициализация Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_your_test_secret_key')
stripe.api_version = "2023-10-16"

# Конфигурация Stripe
STRIPE_CONFIG = {
    'PUBLISHABLE_KEY': os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_your_test_publishable_key'),
    'SECRET_KEY': stripe.api_key,
    'WEBHOOK_SECRET': os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_your_webhook_secret'),
    'SUCCESS_URL': f"{settings.BASE_URL}/api/stripe/success/",
    'CANCEL_URL': f"{settings.BASE_URL}/api/stripe/cancel/",
    'DEFAULT_CURRENCY': 'usd',
}