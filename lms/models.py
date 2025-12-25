from datetime import timezone
from typing import Any

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Course(models.Model):
    """Модель курса."""

    title = models.CharField(max_length=255, verbose_name='Название курса')
    preview = models.ImageField(upload_to='courses/previews/', verbose_name='Превью', blank=True, null=True)
    description = models.TextField(verbose_name='Описание')

    # Добавляем поле владельца
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='courses',
        verbose_name='Владелец'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )

    def save(self, *args, **kwargs):
        # Обновляем поле updated_at при сохранении
        if self.pk:
            self.updated_at = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        ordering = ['-created_at']

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(args, kwargs)
        self.id = None

    def __str__(self):
        return self.title


class Lesson(models.Model):
    """Модель урока."""

    title = models.CharField(max_length=255, verbose_name='Название урока')
    description = models.TextField(verbose_name='Описание')
    preview = models.ImageField(upload_to='lessons/previews/', verbose_name='Превью', blank=True, null=True)
    video_url = models.URLField(verbose_name='Ссылка на видео')

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Курс'
    )

    # Добавляем поле владельца
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lessons',
        verbose_name='Владелец'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )

    def save(self, *args, **kwargs):
        # Обновляем поле updated_at урока и родительского курса
        if self.pk:
            self.updated_at = timezone.now()
            if self.course:
                self.course.save()  # Это обновит updated_at курса
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['created_at']

    def __str__(self):
        return self.title


class Subscription(models.Model):
    """Модель подписки на обновления курса."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Пользователь'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Курс'
    )

    subscribed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата подписки'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        unique_together = ['user', 'course']  # Одна подписка на пользователя и курс
        ordering = ['-subscribed_at']

    def __str__(self):
        return f"{self.user.email} подписан на {self.course.title}"


class Payment(models.Model):
    """Модель платежа."""

    # ... существующие поля ...

    # Поля для Stripe
    stripe_product_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='ID продукта в Stripe'
    )

    stripe_price_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='ID цены в Stripe'
    )

    stripe_session_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='ID сессии в Stripe'
    )

    stripe_payment_intent_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='ID платежа в Stripe'
    )

    stripe_payment_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Ссылка на оплату Stripe'
    )

    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Ожидает оплаты'),
            ('processing', 'В обработке'),
            ('succeeded', 'Успешно'),
            ('failed', 'Неудачно'),
            ('refunded', 'Возвращено'),
        ],
        default='pending',
        verbose_name='Статус платежа'
    )