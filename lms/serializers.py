from rest_framework import serializers
from .models import Course, Lesson


class LessonSerializer(serializers.ModelSerializer):
    """Сериализатор для урока."""

    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Lesson
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'owner']

    def validate(self, data):
        """Дополнительная валидация."""
        request = self.context.get('request')

        # При создании проверяем, что курс принадлежит пользователю (если пользователь не модератор/админ)
        if request and request.method == 'POST':
            course = data.get('course')
            if course and course.owner and course.owner != request.user:
                # Проверяем, является ли пользователь модератором или админом
                if not (request.user.is_staff or
                        request.user.groups.filter(name='moderators').exists()):
                    raise serializers.ValidationError(
                        "Вы можете создавать уроки только в своих курсах."
                    )

        return data

    def create(self, validated_data):
        """Переопределяем create для правильной установки владельца."""
        request = self.context.get('request')
        if request and request.user:
            validated_data['owner'] = request.user
        return super().create(validated_data)


class CourseSerializer(serializers.ModelSerializer):
    """Сериализатор для курса."""

    lessons_count = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)
    owner_email = serializers.EmailField(source='owner.email', read_only=True)

    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'owner']

    def get_lessons_count(self, obj):
        """Получаем количество уроков в курсе."""
        return obj.lessons.count()