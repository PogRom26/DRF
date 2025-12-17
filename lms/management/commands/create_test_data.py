from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from lms.models import Course, Lesson
from decimal import Decimal
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Создает тестовые курсы и уроки для разных владельцев'

    def handle(self, *args, **kwargs):
        # Получаем пользователей
        admin = User.objects.filter(email='admin@example.com').first()
        moderator = User.objects.filter(email='moderator@example.com').first()
        student1 = User.objects.filter(email='student1@example.com').first()
        student2 = User.objects.filter(email='student2@example.com').first()

        if not all([admin, moderator, student1, student2]):
            self.stdout.write(self.style.ERROR('Сначала создайте пользователей через init_data'))
            return

        # Создаем курсы для разных владельцев

        # Курс админа
        admin_course, created = Course.objects.get_or_create(
            title='Курс админа: Продвинутый Python',
            defaults={
                'description': 'Продвинутые темы программирования на Python',
                'owner': admin
            }
        )

        # Курс модератора
        moderator_course, created = Course.objects.get_or_create(
            title='Курс модератора: Основы веб-разработки',
            defaults={
                'description': 'Основы HTML, CSS и JavaScript для начинающих',
                'owner': moderator
            }
        )

        # Курс студента 1
        student1_course, created = Course.objects.get_or_create(
            title='Курс студента 1: Фреймворк Vue.js',
            defaults={
                'description': 'Изучение современного фреймворка Vue.js',
                'owner': student1
            }
        )

        # Курс студента 2
        student2_course, created = Course.objects.get_or_create(
            title='Курс студента 2: Базы данных MySQL',
            defaults={
                'description': 'Работа с реляционными базами данных MySQL',
                'owner': student2
            }
        )

        # Создаем уроки для каждого курса
        courses = [admin_course, moderator_course, student1_course, student2_course]

        for course in courses:
            for i in range(1, 4):  # По 3 урока на курс
                lesson_title = f'Урок {i} курса "{course.title}"'

                if not Lesson.objects.filter(title=lesson_title, course=course).exists():
                    Lesson.objects.create(
                        title=lesson_title,
                        description=f'Содержание урока {i} курса {course.title}. '
                                    f'Владелец: {course.owner.email}',
                        video_url=f'https://www.youtube.com/watch?v={course.id}_lesson_{i}',
                        course=course,
                        owner=course.owner
                    )

        self.stdout.write(self.style.SUCCESS('Созданы тестовые курсы и уроки для разных владельцев'))
        self.stdout.write(f'  - Курс админа: {admin_course.title}')
        self.stdout.write(f'  - Курс модератора: {moderator_course.title}')
        self.stdout.write(f'  - Курс студента 1: {student1_course.title}')
        self.stdout.write(f'  - Курс студента 2: {student2_course.title}')