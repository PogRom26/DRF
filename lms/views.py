from rest_framework import generics
from rest_framework import viewsets
from .models import Course, Lesson
from .serializers import CourseSerializer, LessonSerializer


class LessonListCreateAPIView(generics.ListCreateAPIView):
    """Представление для получения списка уроков и создания нового урока."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer


class LessonRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Представление для получения, обновления и удаления одного урока."""

    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer


class CourseViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с курсами (CRUD)."""

    queryset = Course.objects.all()
    serializer_class = CourseSerializer