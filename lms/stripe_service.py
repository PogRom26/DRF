import logging

logger = logging.getLogger(__name__)


class StripeService:
    """Заглушка сервиса для работы с Stripe API."""

    def __init__(self):
        pass

    def create_payment_for_course(self, course, user):
        """Заглушка для создания платежа."""
        return {
            'success': True,
            'payment_url': 'https://stripe.com/test',
            'message': 'Stripe integration will be implemented'
        }