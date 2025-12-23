import stripe
import os
from django.conf import settings
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class StripeService:
    """Сервис для работы с Stripe API."""

    def __init__(self):
        # Используем ключ из настроек Django (который загружается из .env)
        self.api_key = settings.STRIPE_SECRET_KEY

        if not self.api_key:
            raise ValueError("STRIPE_SECRET_KEY не установлен в настройках. Проверьте .env файл.")

        stripe.api_key = self.api_key
        stripe.api_version = "2023-10-16"

        logger.info(f"Stripe service initialized with key: {self.api_key[:10]}...")

    def create_product(self, name, description=None, metadata=None):
        """
        Создает продукт в Stripe.

        Args:
            name (str): Название продукта
            description (str): Описание продукта
            metadata (dict): Дополнительные метаданные

        Returns:
            dict: Ответ от Stripe
        """
        try:
            product_data = {
                'name': name,
                'description': description or '',
                'metadata': metadata or {}
            }

            product = stripe.Product.create(**product_data)
            logger.info(f"Product created: {product.id}")

            return {
                'success': True,
                'product_id': product.id,
                'product': product
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating product: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }

    def create_price(self, product_id, unit_amount, currency='usd', recurring=None):
        """
        Создает цену для продукта в Stripe.
        Важно: сумма указывается в центах/копейках!

        Args:
            product_id (str): ID продукта в Stripe
            unit_amount (Decimal|float|int): Сумма в минимальных единицах валюты
            currency (str): Валюта (usd, eur, rub и т.д.)
            recurring (dict): Настройки для подписок

        Returns:
            dict: Ответ от Stripe
        """
        try:
            # Конвертируем сумму в целое число (копейки/центы)
            if isinstance(unit_amount, Decimal):
                unit_amount_cents = int(unit_amount * 100)
            elif isinstance(unit_amount, float):
                unit_amount_cents = int(unit_amount * 100)
            else:
                unit_amount_cents = int(unit_amount)

            price_data = {
                'product': product_id,
                'unit_amount': unit_amount_cents,
                'currency': currency.lower(),
                'active': True,
            }

            if recurring:
                price_data['recurring'] = recurring
            else:
                price_data['recurring'] = None

            price = stripe.Price.create(**price_data)
            logger.info(f"Price created: {price.id} - {unit_amount_cents} {currency}")

            return {
                'success': True,
                'price_id': price.id,
                'price': price,
                'unit_amount_cents': unit_amount_cents
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating price: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }

    def create_checkout_session(self, price_id, success_url=None, cancel_url=None, metadata=None):
        """
        Создает сессию Checkout в Stripe.

        Args:
            price_id (str): ID цены в Stripe
            success_url (str): URL для перенаправления после успешной оплаты
            cancel_url (str): URL для перенаправления при отмене
            metadata (dict): Дополнительные метаданные

        Returns:
            dict: Ответ от Stripe
        """
        try:
            # URL по умолчанию из настроек
            if not success_url:
                success_url = f"{settings.BASE_URL}/api/stripe/success/?session_id={{CHECKOUT_SESSION_ID}}"

            if not cancel_url:
                cancel_url = f"{settings.BASE_URL}/api/stripe/cancel/"

            session_data = {
                'payment_method_types': ['card'],
                'line_items': [{
                    'price': price_id,
                    'quantity': 1,
                }],
                'mode': 'payment',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': metadata or {},
            }

            session = stripe.checkout.Session.create(**session_data)
            logger.info(f"Checkout session created: {session.id}")

            return {
                'success': True,
                'session_id': session.id,
                'session_url': session.url,
                'session': session
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }

    def retrieve_session(self, session_id):
        """
        Получает информацию о сессии Checkout.

        Args:
            session_id (str): ID сессии в Stripe

        Returns:
            dict: Информация о сессии
        """
        try:
            session = stripe.checkout.Session.retrieve(session_id)

            return {
                'success': True,
                'session': session,
                'payment_status': session.payment_status,
                'status': session.status
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error retrieving session: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }

    def create_payment_for_course(self, course, user):
        """
        Создает полный платежный процесс для курса.

        Args:
            course (Course): Объект курса
            user (User): Объект пользователя

        Returns:
            dict: Результат создания платежа
        """
        try:
            # Проверяем, есть ли у курса цена
            if not hasattr(course, 'price') or not course.price:
                course.price = Decimal('100.00')  # Цена по умолчанию 100 USD

            # 1. Создаем продукт в Stripe
            product_result = self.create_product(
                name=course.title,
                description=course.description[:500] if course.description else '',  # Ограничиваем длину
                metadata={
                    'course_id': str(course.id),
                    'course_title': course.title[:100],
                    'user_id': str(user.id),
                    'user_email': user.email[:100]
                }
            )

            if not product_result['success']:
                return product_result

            # 2. Создаем цену в Stripe
            price_result = self.create_price(
                product_id=product_result['product_id'],
                unit_amount=course.price,
                currency='usd'  # Можно сделать настраиваемым
            )

            if not price_result['success']:
                return price_result

            # 3. Создаем сессию Checkout
            success_url = f"{settings.BASE_URL}/api/stripe/success/?session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{settings.BASE_URL}/api/stripe/cancel/"

            session_result = self.create_checkout_session(
                price_id=price_result['price_id'],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': str(user.id),
                    'user_email': user.email,
                    'course_id': str(course.id),
                    'course_title': course.title
                }
            )

            if not session_result['success']:
                return session_result

            return {
                'success': True,
                'product_id': product_result['product_id'],
                'price_id': price_result['price_id'],
                'session_id': session_result['session_id'],
                'payment_url': session_result['session_url'],
                'amount': course.price,
                'currency': 'usd',
                'message': 'Платежная сессия создана успешно'
            }

        except Exception as e:
            logger.error(f"Error creating payment for course: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }