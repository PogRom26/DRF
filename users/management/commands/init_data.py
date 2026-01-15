import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from lms.models import Course, Lesson
from users.models import Payment

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Инициализирует тестовые данные: группы, пользователей, курсы, уроки, платежи"
    )

    def handle(self, *args, **kwargs):
        """Основной метод для создания тестовых данных."""
        self.stdout.write("Начинаем создание тестовых данных...")

        groups = self._create_groups()
        self._create_users(groups)
        courses = self._create_courses()
        lessons = self._create_lessons(courses)
        payments_created = self._create_payments(courses, lessons)

        self._print_summary(payments_created)

        self.stdout.write(self.style.SUCCESS("Тестовые данные успешно созданы!"))

    def _create_groups(self):
        """Создает группы пользователей."""
        moderators_group, _ = Group.objects.get_or_create(name="moderators")
        students_group, _ = Group.objects.get_or_create(name="students")

        self.stdout.write(self.style.SUCCESS("Созданы группы: moderators, students"))
        return {"moderators": moderators_group, "students": students_group}

    def _create_users(self, groups):
        """Создает тестовых пользователей."""
        self._create_superuser(groups)
        self._create_moderator(groups)
        self._create_students(groups)

    def _create_superuser(self, groups):
        """Создает суперпользователя."""
        if not User.objects.filter(email="admin@example.com").exists():
            admin = User.objects.create_superuser(
                email="admin@example.com",
                password="admin123",
                first_name="Админ",
                last_name="Админов",
                phone="+79999999999",
                city="Москва",
            )
            admin.groups.add(groups["moderators"])
            self.stdout.write(
                self.style.SUCCESS("Создан суперпользователь (админ и модератор)")
            )

    def _create_moderator(self, groups):
        """Создает тестового модератора."""
        if not User.objects.filter(email="moderator@example.com").exists():
            moderator = User.objects.create_user(
                email="moderator@example.com",
                password="moderator123",
                first_name="Модератор",
                last_name="Тестовый",
                phone="+79998887766",
                city="Санкт-Петербург",
            )
            moderator.groups.add(groups["moderators"])
            self.stdout.write(self.style.SUCCESS("Создан тестовый модератор"))

    def _create_students(self, groups):
        """Создает тестовых студентов."""

        students_data = [
            {"email": "student1@example.com", "first_name": "Иван", "last_name": "Иванов"},
            {"email": "student2@example.com", "first_name": "Мария", "last_name": "Петрова"},
            {"email": "student3@example.com", "first_name": "Алексей", "last_name": "Сидоров"},
        ]

        for student_data in students_data:
            if not User.objects.filter(email=student_data["email"]).exists():
                user = User.objects.create_user(
                    email=student_data["email"],
                    password="password123",
                    first_name=student_data["first_name"],
                    last_name=student_data["last_name"],
                    phone=f"+7999{random.randint(1000000, 9999999)}",
                    city=random.choice(["Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург"]),
                )
                user.groups.add(groups["students"])

        self.stdout.write(self.style.SUCCESS("Созданы студенты"))

    def _create_courses(self):
        """Создает тестовые курсы."""
        admin = User.objects.filter(email="admin@example.com").first()

        courses_data = [
            {
                "title": "Python для начинающих",
                "description": "Полный курс по основам программирования на Python",
                "owner": admin,
            },
            {
                "title": "Django и DRF",
                "description": "Создание веб-приложений с использованием Django и Django REST Framework",
                "owner": admin,
            },
            {
                "title": "JavaScript современный",
                "description": "Изучение современных возможностей JavaScript и фреймворков",
                "owner": admin,
            },
            {
                "title": "Базы данных и SQL",
                "description": "Основы работы с базами данных и языком запросов SQL",
                "owner": admin,
            },
        ]

        courses = []
        for course_data in courses_data:
            course, created = Course.objects.get_or_create(
                title=course_data["title"],
                defaults=course_data
            )
            if created:
                courses.append(course)

        self.stdout.write(self.style.SUCCESS("Созданы курсы"))
        return courses

    def _create_lessons(self, courses):
        """Создает тестовые уроки."""
        lessons = []

        for course in courses:
            for i in range(1, 6):  # По 5 уроков на каждый курс
                lesson_data = {
                    "title": f'Урок {i}: Основы курса "{course.title}"',
                    "description": f'Подробное описание урока {i} курса "{course.title}".',
                    "video_url": f"https://www.youtube.com/watch?v=lesson_{course.id}_{i}",
                    "course": course,
                    "owner": course.owner,
                }

                lesson, created = Lesson.objects.get_or_create(
                    title=lesson_data["title"],
                    course=course,
                    defaults=lesson_data
                )

                if created:
                    lessons.append(lesson)

        self.stdout.write(self.style.SUCCESS("Созданы уроки"))
        return lessons

    def _create_payments(self, courses, lessons):
        """Создает тестовые платежи."""
        # Очищаем старые платежи
        Payment.objects.all().delete()

        users = User.objects.all()

        payments_created = 0
        for i in range(30):  # Создаем 30 тестовых платежей
            user = random.choice(users)

            # Выбираем, оплачиваем курс или урок
            if random.choice([True, False]) and courses:
                course = random.choice(courses)
                lesson = None
                amount = Decimal(random.uniform(5000, 20000)).quantize(Decimal("0.00"))
            elif lessons:
                course = None
                lesson = random.choice(lessons)
                amount = Decimal(random.uniform(500, 3000)).quantize(Decimal("0.00"))
            else:
                continue

            # Определяем способ оплаты
            payment_method = random.choice(["cash", "transfer"])

            # Случайная дата в последние 90 дней
            days_ago = random.randint(0, 90)
            payment_date = datetime.now() - timedelta(days=days_ago)

            try:
                payment = Payment.objects.create(
                    user=user,
                    course=course,
                    lesson=lesson,
                    amount=amount,
                    payment_method=payment_method,
                    payment_date=payment_date,
                )
                payments_created += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Ошибка при создании платежа: {e}"))

        self.stdout.write(
            self.style.SUCCESS(f"Успешно создано {payments_created} платежей")
        )
        return payments_created

    def _print_summary(self, payments_created):
        """Выводит информацию для тестирования."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("ДАННЫЕ ДЛЯ ТЕСТИРОВАНИЯ:")
        self.stdout.write("=" * 50)
        self.stdout.write("Администратор:")
        self.stdout.write("  Email: admin@example.com")
        self.stdout.write("  Пароль: admin123")
        self.stdout.write(
            "  Группы: moderators (автоматически), is_staff=True, is_superuser=True"
        )
        self.stdout.write("\nМодератор:")
        self.stdout.write("  Email: moderator@example.com")
        self.stdout.write("  Пароль: moderator123")
        self.stdout.write("  Группы: moderators")
        self.stdout.write("\nСтуденты:")
        self.stdout.write(
            "  Email: student1@example.com, student2@example.com, student3@example.com"
        )
        self.stdout.write("  Пароль: password123")
        self.stdout.write("  Группы: students")
        self.stdout.write("\nТестируйте доступ:")
        self.stdout.write("  1. Студенты могут только просматривать курсы/уроки")
        self.stdout.write(
            "  2. Модераторы могут просматривать и редактировать, но не создавать/удалять"
        )
        self.stdout.write("  3. Админы могут все")
        self.stdout.write(f"\nСоздано платежей: {payments_created}")
        self.stdout.write("=" * 50)
