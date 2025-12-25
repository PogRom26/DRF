import logging
import os
from decimal import Decimal

import stripe
from django.conf import settings

logger = logging.getLogger(__name__)


class StripeService:
    """Сервис для работы с Stripe API."""

    def __init__(self):
        # Используем ключ из настроек Django (который загружается из .env)
        self.api_key = settings.STRIPE_SECRET_KEY

        if not self.api_key or self.api_key == 'sk_test_your_test_key_here':
            raise ValueError(
                "STRIPE_SECRET_KEY не установлен в настройках. "
                "Проверьте .env файл или установите переменную окружения."
            )

        stripe.api_key = self.api_key
        stripe.api_version = "2023-10-16"

        logger.info(f"Stripe service initialized with key: {self.api_key[:10]}...")

    def create_product(self, name, description=None, metadata=None):
        """Создает продукт в Stripe."""
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

    def create_price(self, product_id, price_amount, currency='usd'):
        """
        Создает цену для продукта в Stripe.

        Args:
            product_id (str): ID продукта в Stripe
            price_amount (Decimal): Цена в долларах (например, 100.00)
            currency (str): Валюта

        Returns:
            dict: Ответ от Stripe
        """
        try:
            # Конвертируем сумму в центы (Stripe требует сумму в минимальных единицах валюты)
            price_cents = int(price_amount * 100)

            price_data = {
                'product': product_id,
                'unit_amount': price_cents,
                'currency': currency.lower(),
                'active': True,
            }

            price = stripe.Price.create(**price_data)
            logger.info(f"Price created: {price.id} - {price_cents} cents {currency}")

            return {
                'success': True,
                'price_id': price.id,
                'price': price,
                'price_cents': price_cents
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating price: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }

    def create_checkout_session(self, price_id, success_url=None, cancel_url=None, metadata=None):
        """Создает сессию Checkout в Stripe."""
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

    def create_payment_for_course(self, course_title, course_description, price_amount, user_id, user_email, course_id,
                                  currency='usd'):
        """
        Создает полный платежный процесс для курса.

        Args:
            course_title (str): Название курса
            course_description (str): Описание курса
            price_amount (Decimal): Цена курса
            user_id (int/str): ID пользователя
            user_email (str): Email пользователя
            course_id (int/str): ID курса
            currency (str): Валюта

        Returns:
            dict: Результат создания платежа в Stripe
        """
        try:
            # 1. Создаем продукт в Stripe
            product_result = self.create_product(
                name=course_title,
                description=course_description[:500] if course_description else '',
                metadata={
                    'course_id': str(course_id),
                    'course_title': course_title[:100],
                    'user_id': str(user_id),
                    'user_email': user_email[:100]
                }
            )

            if not product_result['success']:
                return product_result

            # 2. Создаем цену в Stripe (передаем price_amount как аргумент)
            price_result = self.create_price(
                product_id=product_result['product_id'],
                price_amount=price_amount,
                currency=currency
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
                    'user_id': str(user_id),
                    'user_email': user_email,
                    'course_id': str(course_id),
                    'course_title': course_title,
                    'price': str(price_amount)
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
                'amount': price_amount,
                'currency': currency,
                'message': 'Платежная сессия Stripe создана успешно'
            }

        except Exception as e:
            logger.error(f"Error creating Stripe payment for course: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }

    def create_payment_for_lesson(self, lesson_title, lesson_description, price_amount, user_id, user_email, lesson_id,
                                  currency='usd'):
        """
        Создает платежный процесс для урока.

        Args:
            lesson_title (str): Название урока
            lesson_description (str): Описание урока
            price_amount (Decimal): Цена урока
            user_id (int/str): ID пользователя
            user_email (str): Email пользователя
            lesson_id (int/str): ID урока
            currency (str): Валюта

        Returns:
            dict: Результат создания платежа в Stripe
        """
        try:
            # Аналогично create_payment_for_course, но для урока
            product_result = self.create_product(
                name=f"Урок: {lesson_title}",
                description=lesson_description[:500] if lesson_description else '',
                metadata={
                    'lesson_id': str(lesson_id),
                    'lesson_title': lesson_title[:100],
                    'user_id': str(user_id),
                    'user_email': user_email[:100],
                    'type': 'lesson'
                }
            )

            if not product_result['success']:
                return product_result

            price_result = self.create_price(
                product_id=product_result['product_id'],
                price_amount=price_amount,
                currency=currency
            )

            if not price_result['success']:
                return price_result

            success_url = f"{settings.BASE_URL}/api/stripe/success/?session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{settings.BASE_URL}/api/stripe/cancel/"

            session_result = self.create_checkout_session(
                price_id=price_result['price_id'],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': str(user_id),
                    'user_email': user_email,
                    'lesson_id': str(lesson_id),
                    'lesson_title': lesson_title,
                    'price': str(price_amount),
                    'type': 'lesson'
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
                'amount': price_amount,
                'currency': currency,
                'message': 'Платежная сессия Stripe для урока создана успешно'
            }

        except Exception as e:
            logger.error(f"Error creating Stripe payment for lesson: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }