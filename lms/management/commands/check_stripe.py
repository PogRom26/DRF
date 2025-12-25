import stripe
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Проверка подключения к Stripe API'

    def handle(self, *args, **kwargs):
        self.stdout.write("🔍 Проверка настроек Stripe...")

        # Проверяем наличие ключей
        if not settings.STRIPE_SECRET_KEY:
            self.stdout.write(self.style.ERROR("❌ STRIPE_SECRET_KEY не установлен в настройках"))
            self.stdout.write("   Добавьте в .env файл: STRIPE_SECRET_KEY=sk_test_...")
            return

        if not settings.STRIPE_PUBLISHABLE_KEY:
            self.stdout.write(self.style.WARNING("⚠️  STRIPE_PUBLISHABLE_KEY не установлен"))

        # Проверяем подключение к Stripe
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY

            # Пробуем получить баланс (простой запрос для проверки)
            balance = stripe.Balance.retrieve()

            self.stdout.write(self.style.SUCCESS("✅ Подключение к Stripe успешно!"))
            self.stdout.write(f"   Режим: {'LIVE' if balance.livemode else 'TEST'}")
            self.stdout.write(
                f"   Доступно: {balance.available[0].amount / 100:.2f} {balance.available[0].currency.upper()}")

            # Показываем ключи (первые 10 символов)
            self.stdout.write(f"   Secret Key: {settings.STRIPE_SECRET_KEY[:10]}...")
            if settings.STRIPE_PUBLISHABLE_KEY:
                self.stdout.write(f"   Publishable Key: {settings.STRIPE_PUBLISHABLE_KEY[:10]}...")

        except stripe.error.AuthenticationError as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка аутентификации Stripe: {e}"))
            self.stdout.write("   Проверьте правильность STRIPE_SECRET_KEY в .env файле")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Ошибка при подключении к Stripe: {e}"))