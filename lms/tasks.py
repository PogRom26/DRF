import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from users.models import User

from .models import Course, Lesson, Subscription

logger = logging.getLogger(__name__)


@shared_task
def notify_user_about_course_update(course_id, user_id):
    """Отправляет уведомление конкретному пользователю об обновлении курса."""
    try:
        course = Course.objects.get(id=course_id)
        user = User.objects.get(id=user_id)

        if not user.email or not user.is_active:
            return False

        subject = f"Обновление курса: {course.title}"

        message = f"""
        Здравствуйте, {user.username}!

        Курс "{course.title}" был обновлен.

        Что нового:
        • Добавлены новые материалы
        • Обновлен контент курса
        • Возможно, появились новые задания

        Посмотреть обновления: {settings.BASE_URL}/courses/{course.id}/

        С уважением,
        Команда LMS платформы
        """

        html_message = render_to_string(
            "emails/course_update.html",
            {
                "username": user.username,
                "course_title": course.title,
                "course_url": f"{settings.BASE_URL}/courses/{course.id}/",
                "base_url": settings.BASE_URL,
            },
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(
            f"Уведомление отправлено пользователю {user.email} о курсе {course.title}"
        )
        return True

    except User.DoesNotExist:
        logger.error(f"Пользователь с ID {user_id} не найден")
        return False
    except Course.DoesNotExist:
        logger.error(f"Курс с ID {course_id} не найден")
        return False
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {str(e)}")
        return False


def _process_subscription(subscription, course_id):
    """Обрабатывает одну подписку для отправки уведомления."""
    user = subscription.user

    if not user.email or not user.is_active:
        logger.warning(f"Пропущен пользователь {user.id}: нет email или неактивен")
        return False, True

    try:
        notify_user_about_course_update.delay(course_id, user.id)
        logger.debug(f"Задача отправки уведомления поставлена для пользователя {user.id}")
        return True, False
    except Exception as e:
        logger.error(f"Ошибка при постановке задачи для пользователя {user.id}: {str(e)}")
        return False, True


@shared_task
def send_course_update_notifications(course_id, updated_lesson_id=None):
    """Отправляет уведомления подписчикам курса об обновлении материалов."""
    try:
        course = Course.objects.get(id=course_id)

        subscriptions = Subscription.objects.filter(
            course=course, is_active=True
        ).select_related("user")

        subscriber_count = subscriptions.count()

        if subscriber_count == 0:
            logger.info(f"Нет активных подписчиков для курса {course.title}")
            return "Нет активных подписчиков"

        if updated_lesson_id:
            try:
                updated_lesson = Lesson.objects.get(id=updated_lesson_id)
                logger.info(f"Обновлен урок: {updated_lesson.title}")
            except Lesson.DoesNotExist:
                logger.warning(f"Урок с ID {updated_lesson_id} не найден")

        successful_sends = 0
        failed_sends = 0

        for subscription in subscriptions:
            success, failed = _process_subscription(subscription, course_id)
            if success:
                successful_sends += 1
            if failed:
                failed_sends += 1

        logger.info(
            f"Уведомления отправлены для курса {course.title}. "
            f"Успешно: {successful_sends}, Неудачно: {failed_sends}"
        )

        return f"Отправлено {successful_sends} из {subscriber_count} уведомлений"

    except Course.DoesNotExist:
        logger.error(f"Курс с ID {course_id} не найден")
        return "Курс не найден"
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений: {str(e)}")
        raise


@shared_task
def send_daily_statistics():
    """Отправляет ежедневную статистику администраторам."""
    try:
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_courses = Course.objects.count()
        total_lessons = Lesson.objects.count()

        yesterday = timezone.now() - timedelta(days=1)
        new_users = User.objects.filter(date_joined__gte=yesterday).count()
        new_courses = Course.objects.filter(created_at__gte=yesterday).count()

        subject = f'Ежедневная статистика LMS - {timezone.now().strftime("%d.%m.%Y")}'

        message = f"""
        Ежедневная статистика LMS платформы

        Дата: {timezone.now().strftime('%d.%m.%Y %H:%M')}

        Пользователи:
        - Всего пользователей: {total_users}
        - Активных пользователей: {active_users}
        - Новых пользователей за сутки: {new_users}

        Контент:
        - Всего курсов: {total_courses}
        - Всего уроков: {total_lessons}
        - Новых курсов за сутки: {new_courses}

        ---
        С уважением,
        Система мониторинга LMS
        """

        html_message = render_to_string(
            "emails/daily_statistics.html",
            {
                "date": timezone.now().strftime("%d.%m.%Y %H:%M"),
                "total_users": total_users,
                "active_users": active_users,
                "new_users": new_users,
                "total_courses": total_courses,
                "total_lessons": total_lessons,
                "new_courses": new_courses,
                "base_url": settings.BASE_URL,
            },
        )

        admin_users = User.objects.filter(is_staff=True, is_active=True)
        admin_emails = [admin.email for admin in admin_users if admin.email]

        if admin_emails:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                html_message=html_message,
                fail_silently=True,
            )

            logger.info(f"Ежедневная статистика отправлена {len(admin_emails)} администраторам")
            return f"Статистика отправлена {len(admin_emails)} администраторам"
        else:
            logger.warning("Нет email адресов администраторов для отправки статистики")
            return "Нет email адресов администраторов"

    except Exception as e:
        logger.error(f"Ошибка при отправке ежедневной статистики: {str(e)}")
        raise


@shared_task
def check_and_send_course_update_notifications(
    course_id, updated_lesson_id=None, force_send=False
):
    """Проверяет, нужно ли отправлять уведомление об обновлении курса."""
    try:
        course = Course.objects.get(id=course_id)

        time_since_last_update = timezone.now() - course.updated_at

        if time_since_last_update < timedelta(hours=4) and not force_send:
            logger.info(
                f"Курс {course.title} обновлялся менее 4 часов назад. "
                "Уведомления не отправляются."
            )
            return "Курс обновлялся менее 4 часов назад"

        return send_course_update_notifications.delay(course_id, updated_lesson_id)

    except Course.DoesNotExist:
        logger.error(f"Курс с ID {course_id} не найден")
        return "Курс не найден"
    except Exception as e:
        logger.error(f"Ошибка при проверке обновления курса: {str(e)}")
        raise


@shared_task
def cleanup_old_tasks():
    """Очистка старых выполненных задач Celery."""
    try:
        from celery.backends.database.models import TaskResult

        seven_days_ago = timezone.now() - timedelta(days=7)
        deleted_count, _ = TaskResult.objects.filter(
            date_done__lt=seven_days_ago
        ).delete()

        logger.info(f"Очищено {deleted_count} старых задач Celery")
        return f"Очищено {deleted_count} задач"

    except ImportError:
        logger.warning("Не удалось импортировать TaskResult. Пропускаем очистку.")
        return "Очистка задач недоступна"
    except Exception as e:
        logger.error(f"Ошибка при очистке задач: {str(e)}")
        return f"Ошибка очистки: {str(e)}"
