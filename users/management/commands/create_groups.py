from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from lms.models import Course, Lesson
from users.models import Payment, User


class Command(BaseCommand):
    help = "Создает группы пользователей и назначает им права"

    def handle(self, *args, **kwargs):
        # Создаем группы
        moderators_group, created = Group.objects.get_or_create(name="moderators")
        students_group, created = Group.objects.get_or_create(name="students")

        # Получаем контент-тайпы
        course_ct = ContentType.objects.get_for_model(Course)
        lesson_ct = ContentType.objects.get_for_model(Lesson)
        ContentType.objects.get_for_model(User)
        ContentType.objects.get_for_model(Payment)

        # Получаем все доступные права
        Permission.objects.all()

        # Права для модераторов (просмотр и изменение курсов и уроков)
        # view, change для курсов
        moderators_permissions = Permission.objects.filter(
            content_type__in=[course_ct, lesson_ct],
            codename__in=[
                "view_course",
                "change_course",
                "view_lesson",
                "change_lesson",
            ],
        )

        # Назначаем права группе модераторов
        moderators_group.permissions.set(moderators_permissions)

        # Права для студентов (только просмотр)
        students_permissions = Permission.objects.filter(
            content_type__in=[course_ct, lesson_ct],
            codename__in=["view_course", "view_lesson"],
        )

        # Назначаем права группе студентов
        students_group.permissions.set(students_permissions)

        self.stdout.write(
            self.style.SUCCESS(
                f"Созданы группы: "
                f"модераторы ({moderators_group.permissions.count()} прав), "
                f"студенты ({students_group.permissions.count()} прав)"
            )
        )
