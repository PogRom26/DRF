from rest_framework import generics
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from users.permissions import IsAdminOrModeratorOrReadOnly, IsAdminOrModerator, IsModerator
from .models import Course, Lesson
from .serializers import CourseSerializer, LessonSerializer


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
            # Создание доступно только админам (не модераторам!)
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]


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
            # Редактирование доступно админам и модераторам
            permission_classes = [IsAuthenticated, IsAdminOrModerator]
        else:  # DELETE
            # Удаление доступно только админам (не модераторам!)
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с курсами (CRUD)."""

    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_permissions(self):
        """Разные права для разных действий."""
        if self.action == 'list' or self.action == 'retrieve':
            # Просмотр списка и деталей доступен авторизованным
            permission_classes = [IsAuthenticated]
        elif self.action == 'create' or self.action == 'destroy':
            # Создание и удаление доступно только админам
            permission_classes = [IsAdminUser]
        elif self.action in ['update', 'partial_update']:
            # Редактирование доступно админам и модераторам
            permission_classes = [IsAuthenticated, IsAdminOrModerator]
        else:
            # По умолчанию требуем авторизацию
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]