from rest_framework import generics
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .models import Course, Lesson
from .serializers import CourseSerializer, LessonSerializer


class LessonListCreateAPIView(generics.ListCreateAPIView):
    """Представление для получения списка уроков и создания нового урока."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

    def get_permissions(self):
        """Разные права для разных методов."""
        if self.request.method == 'GET':
            permission_classes = [IsAuthenticated]
        else:  # POST, PUT, DELETE
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]


class LessonRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Представление для получения, обновления и удаления одного урока."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

    def get_permissions(self):
        """Разные права для разных методов."""
        if self.request.method == 'GET':
            permission_classes = [IsAuthenticated]
        else:  # PUT, DELETE
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с курсами (CRUD)."""

    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_permissions(self):
        """Разные права для разных действий."""
        if self.action == 'list' or self.action == 'retrieve':
            permission_classes = [IsAuthenticated]
        else:  # create, update, partial_update, destroy
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]