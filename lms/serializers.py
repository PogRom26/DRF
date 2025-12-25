from rest_framework import serializers

from .models import Course, Lesson, Subscription
from .validators import (NoExternalLinksValidator, YouTubeURLValidator,
                         validate_youtube_url)


class LessonSerializer(serializers.ModelSerializer):
    """Сериализатор для урока."""

    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Lesson
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'owner']

        # Добавляем валидаторы
        validators = [
            YouTubeURLValidator(field='video_url'),
            NoExternalLinksValidator(fields=['description'])
        ]

    def validate_video_url(self, value):
        """Дополнительная валидация URL через метод поля."""
        from .validators import validate_youtube_url
        return validate_youtube_url(value)

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
        fields = [
            'id', 'title', 'preview', 'description', 'owner', 'owner_email',
            'created_at', 'updated_at', 'lessons_count', 'lessons'
        ]
        read_only_fields = ['created_at', 'updated_at', 'owner']

        # Добавляем валидатор для проверки внешних ссылок в описании
        validators = [
            NoExternalLinksValidator(fields=['description'])
        ]

    def get_lessons_count(self, obj):
        """Получаем количество уроков в курсе."""
        return obj.lessons.count()


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для подписки."""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Subscription
        fields = ['id', 'user', 'user_email', 'course', 'course_title',
                  'subscribed_at', 'is_active']
        read_only_fields = ['subscribed_at', 'is_active']


class CourseWithSubscriptionSerializer(CourseSerializer):
    """Сериализатор для курса с информацией о подписке пользователя."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = CourseSerializer.Meta.fields + ['is_subscribed']
        read_only_fields = CourseSerializer.Meta.read_only_fields

    def get_is_subscribed(self, obj):
        """Проверяем, подписан ли текущий пользователь на курс."""
        request = self.context.get('request')

        if request and request.user.is_authenticated:
            return obj.subscriptions.filter(user=request.user, is_active=True).exists()

        return False