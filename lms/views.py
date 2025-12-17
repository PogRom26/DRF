from rest_framework import generics
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from users.permissions import (
    IsModerator, IsOwnerOrModeratorOrAdmin,
    IsCourseOwnerOrModeratorOrAdmin, IsNotModerator
)
from .models import Course, Lesson
from .serializers import CourseSerializer, LessonSerializer
from django.db import models


class LessonListCreateAPIView(generics.ListCreateAPIView):
    """Представление для получения списка уроков и создания нового урока."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

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
        elif self.request.method in ['PUT', 'PATCH', 'DELETE']:
            # Редактирование и удаление доступно владельцу, модераторам или админам
            permission_classes = [IsAuthenticated, IsLessonOwnerOrModeratorOrAdmin]
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
            # Удаление доступно владельцу, модераторам или админам
            permission_classes = [IsAuthenticated, IsCourseOwnerOrModeratorOrAdmin]
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