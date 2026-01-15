import logging
from datetime import timedelta

import html2text
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
    """
    Отправляет уведомление конкретному пользователю об обновлении курса.

    Args:
        course_id: ID курса
        user_id: ID пользователя
    """
    try:
        course = Course.objects.get(id=course_id)
        user = User.objects.get(id=user_id)

        if not user.email or not user.is_active:
            return False

        subject = f"Обновление курса: {course.title}"

        # Текстовое сообщение
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

        # HTML версия
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

        logger.info(f"Уведомление отправлено пользователю {user.email} о курсе {course.title}")
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


@shared_task
def send_course_update_notifications(course_id, updated_lesson_id=None):
    """
    Отправляет уведомления подписчикам курса об обновлении материалов.

    Args:
        course_id: ID обновленного курса
        updated_lesson_id: ID обновленного урока (опционально)
    """
    try:
        course = Course.objects.get(id=course_id)

        # Получаем всех подписчиков курса
        subscriptions = Subscription.objects.filter(
            course=course, is_active=True
        ).select_related("user")

        subscriber_count = subscriptions.count()

        if subscriber_count == 0:
            logger.info(f"Нет активных подписчиков для курса {course.title}")
            return "Нет активных подписчиков"

        # Получаем информацию об обновленном уроке, если указан
        updated_lesson = None
        if updated_lesson_id:
            try:
                updated_lesson = Lesson.objects.get(id=updated_lesson_id)
                logger.info(f"Обновлен урок: {updated_lesson.title}")
            except Lesson.DoesNotExist:
                logger.warning(f"Урок с ID {updated_lesson_id} не найден")

        # Отправляем уведомления каждому подписчику
        successful_sends = 0
        failed_sends = 0

        for subscription in subscriptions:
            user = subscription.user

            if not user.email or not user.is_active:
                failed_sends += 1
                logger.warning(f"Пропущен пользователь {user.id}: нет email или неактивен")
                continue

            # Отправляем уведомление через отдельную задачу
            try:
                # Используем delay() для асинхронного выполнения
                notify_user_about_course_update.delay(course_id, user.id)
                successful_sends += 1
                logger.debug(f"Задача отправки уведомления поставлена для пользователя {user.id}")
            except Exception as e:
                failed_sends += 1
                logger.error(f"Ошибка при постановке задачи для пользователя {user.id}: {str(e)}")

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
    """
    Отправляет ежедневную статистику администраторам.
    """
    try:
        # Собираем статистику
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        total_courses = Course.objects.count()
        total_lessons = Lesson.objects.count()

        # Новые пользователи за последние 24 часа
        yesterday = timezone.now() - timedelta(days=1)
        new_users = User.objects.filter(date_joined__gte=yesterday).count()

        # Новые курсы за последние 24 часа
        new_courses = Course.objects.filter(created_at__gte=yesterday).count()

        # Подготавливаем сообщение
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

        # HTML версия
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

        # Получаем email администраторов
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

            logger.info(
                f"Ежедневная статистика отправлена {len(admin_emails)} администраторам"
            )
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
    """
    Проверяет, нужно ли отправлять уведомление об обновлении курса.
    Отправляет только если курс не обновлялся более 4 часов или если force_send=True.
    """
    try:
        course = Course.objects.get(id=course_id)

        # Проверяем, когда курс последний раз обновлялся
        time_since_last_update = timezone.now() - course.updated_at

        # Если курс обновлялся менее 4 часов назад и не принудительная отправка
        if time_since_last_update < timedelta(hours=4) and not force_send:
            logger.info(
                f"Курс {course.title} обновлялся менее 4 часов назад. Уведомления не отправляются."
            )
            return "Курс обновлялся менее 4 часов назад"

        # Если нужно, отправляем уведомления
        return send_course_update_notifications.delay(course_id, updated_lesson_id)

    except Course.DoesNotExist:
        logger.error(f"Курс с ID {course_id} не найден")
        return "Курс не найден"
    except Exception as e:
        logger.error(f"Ошибка при проверке обновления курса: {str(e)}")
        raise


@shared_task
def cleanup_old_tasks():
    """
    Очистка старых выполненных задач Celery (опционально).
    """
    try:
        from celery.backends.database.models import TaskResult

        # Удаляем задачи старше 7 дней
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