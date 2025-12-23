from django.db import models
from rest_framework import generics
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from users.permissions import (
    IsModerator, IsNotModerator, IsOwnerOrAdmin,
    IsLessonOwnerOrModeratorOrAdmin, IsLessonOwnerOrAdmin,
    IsCourseOwnerOrModeratorOrAdmin, IsCourseOwnerOrAdmin
)
from .models import Course, Lesson
from .serializers import CourseSerializer, LessonSerializer
from .paginators import LessonPaginator, CoursePaginator
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes


class LessonListCreateAPIView(generics.ListCreateAPIView):
    """Представление для получения списка уроков и создания нового урока."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    pagination_class = LessonPaginator

    def get_permissions(self):
        """Разные права для разных методов."""
        if self.request.method == 'GET':
            # Просмотр доступен авторизованным пользователям
            permission_classes = [IsAuthenticated]
        else:  # POST - создание
            # Создание доступно авторизованным пользователям, которые НЕ модераторы
            permission_classes = [IsAuthenticated, IsNotModerator]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Автоматически привязываем урок к текущему пользователю при создании."""
        # Привязываем владельца
        serializer.save(owner=self.request.user)

        # Если курс не указан, привязываем пользователя и к курсу тоже
        if serializer.instance.course and not serializer.instance.course.owner:
            serializer.instance.course.owner = self.request.user
            serializer.instance.course.save()


class LessonRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Представление для получения, обновления и удаления одного урока."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

    def get_permissions(self):
        """Разные права для разных методов."""
        if self.request.method == 'GET':
            # Просмотр доступен авторизованным пользователям
            permission_classes = [IsAuthenticated]
        elif self.request.method in ['PUT', 'PATCH']:
            # Редактирование доступно владельцу, модераторам или админам
            permission_classes = [IsAuthenticated, IsLessonOwnerOrModeratorOrAdmin]
        elif self.request.method == 'DELETE':
            # УДАЛЕНИЕ доступно только владельцу или админу (без модераторов!)
            permission_classes = [IsAuthenticated, IsLessonOwnerOrAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Ограничиваем видимость уроков."""
        user = self.request.user

        # Если пользователь не авторизован, возвращаем пустой queryset
        if not user.is_authenticated:
            return Lesson.objects.none()

        # Админы и модераторы видят все уроки
        if user.is_staff or user.groups.filter(name='moderators').exists():
            return Lesson.objects.all()

        # Обычные пользователи видят только свои уроки и уроки из своих курсов
        return Lesson.objects.filter(
            models.Q(owner=user) |
            models.Q(course__owner=user)
        )


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с курсами (CRUD)."""

    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    pagination_class = CoursePaginator



    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от действия."""
        if self.action in ['list', 'retrieve']:
            return CourseWithSubscriptionSerializer
        return CourseSerializer

    def get_permissions(self):
        """Разные права для разных действий."""
        if self.action == 'list':
            # Список курсов доступен авторизованным пользователям
            permission_classes = [IsAuthenticated]
        elif self.action == 'retrieve':
            # Детали курса доступны авторизованным пользователям
            permission_classes = [IsAuthenticated]
        elif self.action == 'create':
            # Создание доступно авторизованным пользователям, которые НЕ модераторы
            permission_classes = [IsAuthenticated, IsNotModerator]
        elif self.action == 'destroy':
            # УДАЛЕНИЕ доступно только владельцу или админу (без модераторов!)
            permission_classes = [IsAuthenticated, IsCourseOwnerOrAdmin]
        elif self.action in ['update', 'partial_update']:
            # Редактирование доступно владельцу, модераторам или админам
            permission_classes = [IsAuthenticated, IsCourseOwnerOrModeratorOrAdmin]
        else:
            # По умолчанию требуем авторизацию
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        """Автоматически привязываем курс к текущему пользователю при создании."""
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        """Ограничиваем видимость курсов."""
        user = self.request.user

        # Если пользователь не авторизован, возвращаем пустой queryset
        if not user.is_authenticated:
            return Course.objects.none()

        # Админы и модераторы видят все курсы
        if user.is_staff or user.groups.filter(name='moderators').exists():
            return Course.objects.all()

        # Обычные пользователи видят только свои курсы
        return Course.objects.filter(owner=user)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def lessons(self, request, pk=None):
        """Получение всех уроков курса."""
        course = self.get_object()

        # Проверяем доступ к курсу
        if not (course.owner == request.user or
                request.user.is_staff or
                request.user.groups.filter(name='moderators').exists()):
            return Response(
                {"detail": "У вас нет доступа к этому курсу."},
                status=403
            )

        lessons = course.lessons.all()
        serializer = LessonSerializer(lessons, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['courses'],
        description='Получить список курсов с пагинацией',
        parameters=[
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Номер страницы'
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Количество элементов на странице (макс. 20)'
            ),
        ],
        responses={
            200: CourseSerializer(many=True),
            401: {'description': 'Не авторизован'},
        }
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        tags=['courses'],
        description='Создать новый курс',
        request=CourseSerializer,
        responses={
            201: CourseSerializer,
            400: {'description': 'Некорректные данные'},
            403: {'description': 'Нет прав на создание курса'},
        },
        examples=[
            OpenApiExample(
                'Пример создания курса',
                value={
                    'title': 'Новый курс',
                    'description': 'Описание нового курса',
                    'preview': None,
                },
                request_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Course, Subscription
from .serializers import SubscriptionSerializer, CourseWithSubscriptionSerializer


class SubscriptionAPIView(APIView):
    """API для управления подписками на курсы."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """Добавление или удаление подписки на курс."""
        user = request.user
        course_id = request.data.get('course_id')

        if not course_id:
            return Response(
                {"error": "Не указан course_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Получаем курс
        course = get_object_or_404(Course, id=course_id)

        # Проверяем существующую подписку
        subscription = Subscription.objects.filter(
            user=user,
            course=course
        ).first()

        if subscription:
            # Если подписка существует - удаляем ее (или деактивируем)
            subscription.delete()
            message = 'Подписка удалена'
            is_subscribed = False
        else:
            # Если подписки нет - создаем новую
            subscription = Subscription.objects.create(
                user=user,
                course=course,
                is_active=True
            )
            message = 'Подписка добавлена'
            is_subscribed = True

        return Response({
            "message": message,
            "is_subscribed": is_subscribed,
            "subscription": SubscriptionSerializer(subscription).data if subscription else None
        })

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
            user=user,
            course=course,
            is_active=True
        ).exists()

        return Response({
            "course_id": course.id,
            "course_title": course.title,
            "is_subscribed": is_subscribed
        })

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


class CreateCoursePaymentAPIView(APIView):
    """Заглушка для создания платежа за курс через Stripe."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response({
            'success': True,
            'message': 'Stripe integration will be implemented here',
            'payment_url': 'https://stripe.com/test'
        })