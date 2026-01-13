import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task
def check_inactive_users():
    """
    Проверяет пользователей по дате последнего входа и блокирует неактивных.
    Задача запускается ежедневно через Celery Beat.
    """
    try:
        # Определяем дату месяц назад
        one_month_ago = timezone.now() - timedelta(days=30)

        # Находим пользователей, которые не заходили более месяца
        inactive_users = User.objects.filter(
            last_login__lt=one_month_ago, is_active=True
        ).exclude(
            is_superuser=True
        )  # Не блокируем суперпользователей

        user_count = inactive_users.count()

        if user_count > 0:
            # Блокируем пользователей
            inactive_users.update(is_active=False)

            # Логируем действие
            logger.info(f"Заблокировано {user_count} неактивных пользователей")

            # Отправляем уведомление администратору
            admin_users = User.objects.filter(is_staff=True)
            admin_emails = [admin.email for admin in admin_users if admin.email]

            if admin_emails:
                send_mail(
                    subject=f"Блокировка неактивных пользователей",
                    message=f"Было заблокировано {user_count} пользователей, которые не заходили в систему более месяца.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=True,
                )

            return f"Заблокировано {user_count} неактивных пользователей"
        else:
            logger.info("Неактивных пользователей для блокировки не найдено")
            return "Неактивных пользователей для блокировки не найдено"

    except Exception as e:
        logger.error(f"Ошибка при блокировке неактивных пользователей: {str(e)}")
        raise


@shared_task
def send_user_notification_email(user_email, subject, message, html_message=None):
    """
    Отправляет уведомительное письмо пользователю.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Письмо отправлено пользователю {user_email}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке письма пользователю {user_email}: {str(e)}")
        return False


@shared_task
def notify_user_about_course_update(course_id, user_id):
    """
    Уведомляет конкретного пользователя об обновлении курса.
    """
    from django.contrib.auth import get_user_model

    from lms.models import Course

    User = get_user_model()

    try:
        user = User.objects.get(id=user_id, is_active=True)
        course = Course.objects.get(id=course_id)

        # Создаем содержимое письма
        subject = f"Обновление курса: {course.title}"

        # Текстовое сообщение
        message = f"""
        Уважаемый(ая) {user.first_name or 'пользователь'}!

        Курс "{course.title}" был обновлен.

        Дата обновления: {timezone.now().strftime('%d.%m.%Y %H:%M')}

        Посмотреть обновления: {settings.BASE_URL}/courses/{course.id}/

        ---
        С уважением,
        Команда LMS платформы
        """

        # HTML сообщение
        html_message = render_to_string(
            "emails/course_update_notification.html",
            {
                "user": user,
                "course": course,
                "update_date": timezone.now().strftime("%d.%m.%Y %H:%M"),
                "course_url": f"{settings.BASE_URL}/courses/{course.id}/",
                "base_url": settings.BASE_URL,
            },
        )

        # Отправляем письмо
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=True,
        )

        logger.info(
            f"Уведомление об обновлении курса отправлено пользователю {user.email}"
        )
        return True

    except User.DoesNotExist:
        logger.error(f"Пользователь с ID {user_id} не найден")
        return False
    except Course.DoesNotExist:
        logger.error(f"Курс с ID {course_id} не найден")
        return False
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления: {str(e)}")
        return False
