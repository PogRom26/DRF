from rest_framework import serializers
from .models import User, Payment
from lms.serializers import CourseSerializer, LessonSerializer


class PaymentSerializer(serializers.ModelSerializer):
    """Сериализатор для платежей."""

    # Добавляем информацию о курсе и уроке
    course_info = CourseSerializer(source='course', read_only=True)
    lesson_info = LessonSerializer(source='lesson', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'payment_date',
            'course', 'lesson', 'course_info', 'lesson_info',
            'amount', 'payment_method', 'payment_method_display'
        ]
        read_only_fields = ['payment_date']

    # Добавляем поле для отображения человекочитаемого способа оплаты
    payment_method_display = serializers.CharField(
        source='get_payment_method_display',
        read_only=True
    )


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя."""

    # Дополнительное задание: история платежей пользователя
    payments = PaymentSerializer(many=True, read_only=True)
    payments_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'phone', 'city', 'avatar', 'date_joined',
            'payments', 'payments_count'
        ]
        read_only_fields = ['date_joined']

    def get_payments_count(self, obj):
        """Количество платежей пользователя."""
        return obj.payments.count()