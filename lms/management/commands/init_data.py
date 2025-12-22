from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from lms.models import Course, Lesson
from users.models import Payment
from decimal import Decimal
import random
from datetime import datetime, timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Инициализирует тестовые данные: пользователи, курсы, уроки, платежи'

    def handle(self, *args, **kwargs):
        self.stdout.write('Начинаем создание тестовых данных...')

        # Создаем суперпользователя
        if not User.objects.filter(email='admin@example.com').exists():
            User.objects.create_superuser(
                email='admin@example.com',
                password='admin123',
                first_name='Админ',
                last_name='Админов',
                phone='+79999999999',
                city='Москва'
            )
            self.stdout.write(self.style.SUCCESS('Создан суперпользователь'))

        # Создаем обычных пользователей
        users_data = [
            {'email': 'user1@example.com', 'first_name': 'Иван', 'last_name': 'Иванов'},
            {'email': 'user2@example.com', 'first_name': 'Мария', 'last_name': 'Петрова'},
            {'email': 'user3@example.com', 'first_name': 'Алексей', 'last_name': 'Сидоров'},
        ]

        for user_data in users_data:
            if not User.objects.filter(email=user_data['email']).exists():
                User.objects.create_user(
                    email=user_data['email'],
                    password='password123',
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    phone=f'+7999{random.randint(1000000, 9999999)}',
                    city=random.choice(['Москва', 'Санкт-Петербург', 'Новосибирск'])
                )

        self.stdout.write(self.style.SUCCESS('Созданы пользователи'))

        # Создаем курсы
        courses_data = [
            {
                'title': 'Python для начинающих',
                'description': 'Полный курс по основам программирования на Python'
            },
            {
                'title': 'Django и DRF',
                'description': 'Создание веб-приложений с использованием Django и Django REST Framework'
            },
            {
                'title': 'JavaScript современный',
                'description': 'Изучение современных возможностей JavaScript и фреймворков'
            },
        ]

        courses = []
        for course_data in courses_data:
            course, created = Course.objects.get_or_create(
                title=course_data['title'],
                defaults=course_data
            )
            if created:
                courses.append(course)

        self.stdout.write(self.style.SUCCESS('Созданы курсы'))

        # Создаем уроки
        lessons_data = []

        for course in courses:
            for i in range(1, 6):  # По 5 уроков на каждый курс
                lesson_data = {
                    'title': f'Урок {i} курса "{course.title}"',
                    'description': f'Описание урока {i} курса "{course.title}"',
                    'video_url': f'https://www.youtube.com/watch?v=lesson_{course.id}_{i}',
                    'course': course
                }
                lesson, created = Lesson.objects.get_or_create(
                    title=lesson_data['title'],
                    course=course,
                    defaults=lesson_data
                )
                if created:
                    lessons_data.append(lesson)

        self.stdout.write(self.style.SUCCESS('Созданы уроки'))

        # Очищаем старые платежи
        Payment.objects.all().delete()

        # Получаем всех пользователей, курсы и уроки
        users = User.objects.all()
        courses = Course.objects.all()
        lessons = Lesson.objects.all()

        # Создаем платежи
        payments_created = 0
        for i in range(30):  # Создаем 30 тестовых платежей
            user = random.choice(users)

            # Выбираем, оплачиваем курс или урок
            if random.choice([True, False]) and courses.exists():
                course = random.choice(courses)
                lesson = None
                amount = Decimal(random.uniform(5000, 20000)).quantize(Decimal('0.00'))
            elif lessons.exists():
                course = None
                lesson = random.choice(lessons)
                amount = Decimal(random.uniform(500, 3000)).quantize(Decimal('0.00'))
            else:
                continue

            # Определяем способ оплаты
            payment_method = random.choice(['cash', 'transfer'])

            # Случайная дата в последние 90 дней
            days_ago = random.randint(0, 90)
            payment_date = datetime.now() - timedelta(days=days_ago)

            try:
                payment = Payment.objects.create(
                    user=user,
                    course=course,
                    lesson=lesson,
                    amount=amount,
                    payment_method=payment_method
                )
                # Обновляем дату вручную
                payment.payment_date = payment_date
                payment.save(update_fields=['payment_date'])
                payments_created += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Ошибка при создании платежа: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Успешно создано {payments_created} платежей'))
        self.stdout.write(self.style.SUCCESS('Тестовые данные успешно созданы!'))