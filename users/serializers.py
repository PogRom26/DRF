from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Payment
from lms.serializers import CourseSerializer, LessonSerializer

User = get_user_model()


class PaymentSerializer(serializers.ModelSerializer):
    """Сериализатор для платежей."""

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

    payment_method_display = serializers.CharField(
        source='get_payment_method_display',
        read_only=True
    )


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя (чтение)."""

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
        return obj.payments.count()


class UserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания пользователя."""

    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True, label='Confirm Password')
    tokens = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'phone', 'city', 'avatar', 'password', 'password2', 'tokens'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'phone': {'required': False},
            'city': {'required': False},
            'avatar': {'required': False},
        }

    def get_tokens(self, obj):
        """Получаем токены для пользователя."""
        refresh = RefreshToken.for_user(obj)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def validate(self, attrs):
        """Валидация данных при регистрации."""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})

        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Пользователь с таким email уже существует"})

        return attrs

    def create(self, validated_data):
        """Создание пользователя."""
        validated_data.pop('password2')
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления пользователя."""

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'phone', 'city', 'avatar'
        ]
        read_only_fields = ['email']  # Email нельзя менять

    def update(self, instance, validated_data):
        """Обновление пользователя."""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class UserLoginSerializer(serializers.Serializer):
    """Сериализатор для входа пользователя."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        """Валидация данных при входе."""
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            try:
                user = User.objects.get(email=email)
                if user.check_password(password):
                    return {'user': user}
                else:
                    raise serializers.ValidationError("Неверный пароль")
            except User.DoesNotExist:
                raise serializers.ValidationError("Пользователь с таким email не найден")
        else:
            raise serializers.ValidationError("Необходимо указать email и пароль")