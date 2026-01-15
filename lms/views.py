import logging
from datetime import timedelta

from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
)
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import (
    IsCourseOwnerOrAdmin,
    IsCourseOwnerOrModeratorOrAdmin,
    IsLessonOwnerOrAdmin,
    IsLessonOwnerOrModeratorOrAdmin,
    IsNotModerator,
)

from .models import Course, Lesson, Subscription
from .paginators import CoursePaginator, LessonPaginator
from .serializers import (
    CourseSerializer,
    CourseWithSubscriptionSerializer,
    LessonSerializer,
    SubscriptionSerializer,
)
from .tasks import (
    check_and_send_course_update_notifications,
    send_course_update_notifications,
)


class LessonListCreateAPIView(generics.ListCreateAPIView):
    """Представление для получения списка уроков и создания нового урока."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    pagination_class = LessonPaginator

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от метода."""
        if self.request.method == "POST":
            return LessonSerializer
        return LessonSerializer

    def get_permissions(self):
        """Разные права для разных методов."""
        if self.request.method == "GET":
            # Просмотр доступен авторизованным пользователям
            permission_classes = [IsAuthenticated]
        else:  # POST - создание
            # Создание доступно авторизованным пользователям, которые НЕ модераторы
            permission_classes = [IsAuthenticated, IsNotModerator]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Автоматически привязываем урок к текущему пользователю при создании."""
        # Привязываем владельца
        lesson = serializer.save(owner=self.request.user)

        # Если курс не указан, привязываем пользователя и к курсу тоже
        if lesson.course and not lesson.course.owner:
            lesson.course.owner = self.request.user
            lesson.course.save()

        logger.info(
            f'Урок "{lesson.title}" создан пользователем {self.request.user.email}'
        )

        # Если урок связан с курсом, проверяем, нужно ли отправить уведомления
        if lesson.course:
            self._check_and_notify_course_subscribers(lesson.course.id)

    def get_queryset(self):
        """Ограничиваем видимость уроков."""
        user = self.request.user

        # Если пользователь не авторизован, возвращаем пустой queryset
        if not user.is_authenticated:
            return Lesson.objects.none()

        # Админы и модераторы видят все уроки
        if user.is_staff or user.groups.filter(name="moderators").exists():
            return Lesson.objects.all()

        # Обычные пользователи видят только свои уроки и уроки из своих курсов
        return Lesson.objects.filter(
            models.Q(owner=user) | models.Q(course__owner=user)
        )

    def _check_and_notify_course_subscribers(self, course_id):
        """Проверяет и отправляет уведомления подписчикам курса."""
        try:
            course = Course.objects.get(id=course_id)

            # Проверяем, когда курс последний раз обновлялся
            time_since_last_update = timezone.now() - course.updated_at

            # Проверяем, есть ли активные подписчики
            has_subscribers = Subscription.objects.filter(
                course=course, is_active=True
            ).exists()

            if has_subscribers and time_since_last_update > timedelta(hours=4):
                # Запускаем асинхронную задачу для отправки уведомлений
                check_and_send_course_update_notifications.delay(
                    course_id=course_id, force_send=True
                )
                logger.info(f"Уведомления для курса {course_id} поставлены в очередь")
            elif has_subscribers:
                logger.info(
                    f"Курс {course.title} обновлялся менее 4 часов назад. Уведомления не отправляются."
                )
            else:
                logger.info(f"У курса {course.title} нет активных подписчиков")

        except Course.DoesNotExist:
            logger.error(f"Курс с ID {course_id} не найден")


class LessonRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Представление для получения, обновления и удаления одного урока."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от метода."""
        if self.request.method in ["PUT", "PATCH"]:
            from .serializers import LessonUpdateSerializer

            return LessonUpdateSerializer
        return LessonSerializer

    def get_permissions(self):
        """Разные права для разных методов."""
        if self.request.method == "GET":
            # Просмотр доступен авторизованным пользователям
            permission_classes = [IsAuthenticated]
        elif self.request.method in ["PUT", "PATCH"]:
            # Редактирование доступно владельцу, модераторам или админам
            permission_classes = [IsAuthenticated, IsLessonOwnerOrModeratorOrAdmin]
        elif self.request.method == "DELETE":
            # УДАЛЕНИЕ доступно только владельцу или админу (без модераторов!)
            permission_classes = [IsAuthenticated, IsLessonOwnerOrAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def perform_update(self, serializer):
        """
        Обновляет урок и отправляет уведомления подписчикам родительского курса.
        """
        # Сохраняем информацию о курсе до обновления
        instance = self.get_object()
        old_course_id = instance.course.id if instance.course else None
        old_updated_at = instance.updated_at

        # Сохраняем обновленный урок
        updated_lesson = serializer.save()

        # Проверяем, действительно ли урок был обновлен
        if old_updated_at != updated_lesson.updated_at:
            logger.info(
                f'Урок "{updated_lesson.title}" обновлен пользователем {self.request.user.email}'
            )

            # Если урок связан с курсом, проверяем, нужно ли отправить уведомления
            if updated_lesson.course:
                self._check_and_notify_course_subscribers(updated_lesson.course.id)

        # Если курс изменился, отправляем уведомления и для нового курса
        if (
            old_course_id
            and updated_lesson.course
            and old_course_id != updated_lesson.course.id
        ):
            logger.info(f'Урок "{updated_lesson.title}" перемещен в другой курс')
            self._check_and_notify_course_subscribers(updated_lesson.course.id)

    def perform_destroy(self, instance):
        """
        Удаляет урок и логирует действие.
        """
        lesson_title = instance.title
        course_id = instance.course.id if instance.course else None
        user_email = self.request.user.email

        instance.delete()

        logger.info(f'Урок "{lesson_title}" удален пользователем {user_email}')

        # Если урок был связан с курсом, обновляем дату курса
        if course_id:
            try:
                course = Course.objects.get(id=course_id)
                course.save()  # Это обновит поле updated_at курса

                # Проверяем, нужно ли отправить уведомления
                self._check_and_notify_course_subscribers(course_id)

            except Course.DoesNotExist:
                pass

    def get_queryset(self):
        """Ограничиваем видимость уроков."""
        user = self.request.user

        # Если пользователь не авторизован, возвращаем пустой queryset
        if not user.is_authenticated:
            return Lesson.objects.none()

        # Админы и модераторы видят все уроки
        if user.is_staff or user.groups.filter(name="moderators").exists():
            return Lesson.objects.all()

        # Обычные пользователи видят только свои уроки и уроки из своих курсов
        return Lesson.objects.filter(
            models.Q(owner=user) | models.Q(course__owner=user)
        )

    def _check_and_notify_course_subscribers(self, course_id):
        """Проверяет и отправляет уведомления подписчикам курса."""
        try:
            course = Course.objects.get(id=course_id)

            # Проверяем, когда курс последний раз обновлялся
            time_since_last_update = timezone.now() - course.updated_at

            # Проверяем, есть ли активные подписчики
            has_subscribers = Subscription.objects.filter(
                course=course, is_active=True
            ).exists()

            if has_subscribers and time_since_last_update > timedelta(hours=4):
                # Запускаем асинхронную задачу для отправки уведомлений
                check_and_send_course_update_notifications.delay(
                    course_id=course_id, force_send=True
                )
                logger.info(f"Уведомления для курса {course_id} поставлены в очередь")
            elif has_subscribers:
                logger.info(
                    f"Курс {course.title} обновлялся менее 4 часов назад. Уведомления не отправляются."
                )
            else:
                logger.info(f"У курса {course.title} нет активных подписчиков")

        except Course.DoesNotExist:
            logger.error(f"Курс с ID {course_id} не найден")




logger = logging.getLogger(__name__)


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с курсами (CRUD)."""

    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    pagination_class = CoursePaginator

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от действия."""
        if self.action in ["list", "retrieve"]:
            return CourseWithSubscriptionSerializer
        return CourseSerializer

    def get_permissions(self):
        """Разные права для разных действий."""
        if self.action == "list":
            # Список курсов доступен авторизованным пользователям
            permission_classes = [IsAuthenticated]
        elif self.action == "retrieve":
            # Детали курса доступны авторизованным пользователям
            permission_classes = [IsAuthenticated]
        elif self.action == "create":
            # Создание доступно авторизованным пользователям, которые НЕ модераторы
            permission_classes = [IsAuthenticated, IsNotModerator]
        elif self.action == "destroy":
            # УДАЛЕНИЕ доступно только владельцу или админу (без модераторов!)
            permission_classes = [IsAuthenticated, IsCourseOwnerOrAdmin]
        elif self.action in ["update", "partial_update"]:
            # Редактирование доступно владельцу, модераторам или админам
            permission_classes = [IsAuthenticated, IsCourseOwnerOrModeratorOrAdmin]
        else:
            # По умолчанию требуем авторизацию
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Автоматически привязываем курс к текущему пользователю при создании."""
        serializer.save(owner=self.request.user)
        logger.info(f"Курс создан пользователем {self.request.user.email}")

    def perform_update(self, serializer):
        """
        Обновляет курс и отправляет уведомления подписчикам.
        """
        # Получаем текущее состояние курса до обновления
        instance = self.get_object()
        old_updated_at = instance.updated_at

        # Сохраняем обновленный курс
        updated_course = serializer.save()

        # Проверяем, действительно ли курс был обновлен
        # (updated_at автоматически обновляется при сохранении)
        if old_updated_at != updated_course.updated_at:
            logger.info(
                f"Курс {updated_course.id} обновлен пользователем {self.request.user.email}"
            )

            # Проверяем, нужно ли отправлять уведомления
            time_since_last_update = timezone.now() - updated_course.updated_at

            # Получаем активных подписчиков курса
            subscribers = Subscription.objects.filter(
                course=updated_course, is_active=True
            ).select_related("user")

            if subscribers.exists():
                # Проверяем, прошел ли 4 часа с последнего обновления
                if time_since_last_update > timedelta(hours=4):
                    # Запускаем асинхронную задачу для отправки уведомлений
                    check_and_send_course_update_notifications.delay(
                        course_id=updated_course.id, force_send=True
                    )
                    logger.info(
                        f"Задача отправки уведомлений для курса {updated_course.id} поставлена в очередь"
                    )
                else:
                    logger.info(
                        f"Курс {updated_course.title} обновлялся менее 4 часов назад. Уведомления не отправляются."
                    )
            else:
                logger.info(f"У курса {updated_course.title} нет активных подписчиков")

    def get_queryset(self):
        """Ограничиваем видимость курсов."""
        user = self.request.user

        # Если пользователь не авторизован, возвращаем пустой queryset
        if not user.is_authenticated:
            return Course.objects.none()

        # Админы и модераторы видят все курсы
        if user.is_staff or user.groups.filter(name="moderators").exists():
            return Course.objects.all()

        # Обычные пользователи видят только свои курсы
        return Course.objects.filter(owner=user)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def lessons(self, request, pk=None):
        """Получение всех уроков курса."""
        course = self.get_object()

        # Проверяем доступ к курсу
        if not (
            course.owner == request.user
            or request.user.is_staff
            or request.user.groups.filter(name="moderators").exists()
        ):
            return Response(
                {"detail": "У вас нет доступа к этому курсу."},
                status=status.HTTP_403_FORBIDDEN,
            )

        lessons = course.lessons.all()
        serializer = LessonSerializer(lessons, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def subscribe(self, request, pk=None):
        """Подписка на обновления курса."""
        course = self.get_object()
        user = request.user

        # Проверяем доступ к курсу (только для своих курсов или если есть доступ)
        if not (
            course.owner == user
            or user.is_staff
            or user.groups.filter(name="moderators").exists()
        ):
            return Response(
                {"detail": "У вас нет доступа к этому курсу."},
                status=status.HTTP_403_FORBIDDEN,
            )

        subscription, created = Subscription.objects.get_or_create(
            user=user, course=course, defaults={"is_active": True}
        )

        if not created:
            subscription.is_active = True
            subscription.save()

        return Response(
            {
                "status": "subscribed",
                "message": f'Вы подписались на обновления курса "{course.title}"',
                "course_id": course.id,
                "subscription_id": subscription.id,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def unsubscribe(self, request, pk=None):
        """Отписка от обновлений курса."""
        course = self.get_object()
        user = request.user

        try:
            subscription = Subscription.objects.get(user=user, course=course)
            subscription.is_active = False
            subscription.save()

            return Response(
                {
                    "status": "unsubscribed",
                    "message": f'Вы отписались от обновлений курса "{course.title}"',
                },
                status=status.HTTP_200_OK,
            )
        except Subscription.DoesNotExist:
            return Response(
                {"error": "Вы не подписаны на этот курс"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def subscribers(self, request, pk=None):
        """Получение списка подписчиков курса (только для владельца, модераторов и админов)."""
        course = self.get_object()
        user = request.user

        # Проверяем права доступа
        if not (
            course.owner == user
            or user.is_staff
            or user.groups.filter(name="moderators").exists()
        ):
            return Response(
                {"detail": "У вас нет прав для просмотра подписчиков."},
                status=status.HTTP_403_FORBIDDEN,
            )

        subscribers = Subscription.objects.filter(
            course=course, is_active=True
        ).select_related("user")

        data = [
            {
                "user_id": sub.user.id,
                "user_email": sub.user.email,
                "user_first_name": sub.user.first_name,
                "user_last_name": sub.user.last_name,
                "subscribed_at": sub.subscribed_at,
                "is_active": sub.is_active,
            }
            for sub in subscribers
        ]

        return Response(data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def test_notification(self, request, pk=None):
        """Тестовая отправка уведомления о курсе (только для владельца, модераторов и админов)."""
        course = self.get_object()
        user = request.user

        # Проверяем права доступа
        if not (
            course.owner == user
            or user.is_staff
            or user.groups.filter(name="moderators").exists()
        ):
            return Response(
                {"detail": "У вас нет прав для тестирования уведомлений."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Запускаем задачу для тестирования уведомления
        result = send_course_update_notifications.delay(course.id, user.id)

        return Response(
            {
                "status": "notification_sent",
                "message": f"Тестовое уведомление отправлено на email {user.email}",
                "task_id": result.id,
                "course_id": course.id,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["courses"],
        description="Получить список курсов с пагинацией",
        parameters=[
            OpenApiParameter(
                name="page",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Номер страницы",
            ),
            OpenApiParameter(
                name="page_size",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Количество элементов на странице (макс. 20)",
            ),
        ],
        responses={
            200: CourseSerializer(many=True),
            401: {"description": "Не авторизован"},
        },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=["courses"],
        description="Получить детальную информацию о курсе",
        responses={
            200: CourseSerializer,
            401: {"description": "Не авторизован"},
            404: {"description": "Курс не найден"},
        },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        tags=["courses"],
        description="Создать новый курс",
        request=CourseSerializer,
        responses={
            201: CourseSerializer,
            400: {"description": "Неверные данные"},
            401: {"description": "Не авторизован"},
            403: {"description": "Нет прав для создания курса"},
        },
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        tags=["courses"],
        description="Обновить курс",
        request=CourseSerializer,
        responses={
            200: CourseSerializer,
            400: {"description": "Неверные данные"},
            401: {"description": "Не авторизован"},
            403: {"description": "Нет прав для обновления курса"},
            404: {"description": "Курс не найден"},
        },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        tags=["courses"],
        description="Создать новый курс",
        request=CourseSerializer,
        responses={
            201: CourseSerializer,
            400: {"description": "Некорректные данные"},
            403: {"description": "Нет прав на создание курса"},
        },
        examples=[
            OpenApiExample(
                "Пример создания курса",
                value={
                    "title": "Новый курс",
                    "description": "Описание нового курса",
                    "preview": None,
                },
                request_only=True,
            )
        ],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class SubscriptionAPIView(APIView):
    """API для управления подписками на курсы."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """Добавление или удаление подписки на курс."""
        user = request.user
        course_id = request.data.get("course_id")

        if not course_id:
            return Response(
                {"error": "Не указан course_id"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Получаем курс
        course = get_object_or_404(Course, id=course_id)

        # Проверяем существующую подписку
        subscription = Subscription.objects.filter(user=user, course=course).first()

        if subscription:
            # Если подписка существует - удаляем ее (или деактивируем)
            subscription.delete()
            message = "Подписка удалена"
            is_subscribed = False
        else:
            # Если подписки нет - создаем новую
            subscription = Subscription.objects.create(
                user=user, course=course, is_active=True
            )
            message = "Подписка добавлена"
            is_subscribed = True

        return Response(
            {
                "message": message,
                "is_subscribed": is_subscribed,
                "subscription": (
                    SubscriptionSerializer(subscription).data if subscription else None
                ),
            }
        )

    def get(self, request, *args, **kwargs):
        """Получение списка подписок пользователя."""
        user = request.user
        subscriptions = Subscription.objects.filter(user=user, is_active=True)
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data)


class CourseSubscriptionAPIView(APIView):
    """API для проверки подписки на конкретный курс."""

    permission_classes = [IsAuthenticated]

    def get(self, request, course_id, *args, **kwargs):
        """Проверка подписки на курс."""
        user = request.user
        course = get_object_or_404(Course, id=course_id)

        is_subscribed = Subscription.objects.filter(
            user=user, course=course, is_active=True
        ).exists()

        return Response(
            {
                "course_id": course.id,
                "course_title": course.title,
                "is_subscribed": is_subscribed,
            }
        )


logger = logging.getLogger(__name__)

class CreateCoursePaymentAPIView(APIView):
    """Заглушка для создания платежа за курс через Stripe."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(
            {
                "success": True,
                "message": "Stripe integration will be implemented here",
                "payment_url": "https://stripe.com/test",
            }
        )
