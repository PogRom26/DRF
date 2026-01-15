from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Инициализирует тестовые данные: пользователи, курсы, уроки, платежи"

    def handle(self, *args, **kwargs):
        """Основной метод для создания тестовых данных."""
        self.stdout.write("Начинаем создание тестовых данных...")
        self._create_all_data()
        self.stdout.write(self.style.SUCCESS("Тестовые данные успешно созданы!"))

    def _create_all_data(self):
        """Создает все тестовые данные."""
        groups = self._create_groups()
        self._create_users(groups)
        courses = self._create_courses()
        lessons = self._create_lessons(courses)
        payments_created = self._create_payments(courses, lessons)
        self._print_summary(payments_created)
