from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from .models import Payment
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    UserLoginSerializer, PaymentSerializer
)
from .filters import PaymentFilter
from .permissions import IsOwnerOrReadOnly, IsOwner

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с пользователями (CRUD)."""

    queryset = User.objects.all()

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от действия."""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        """Настройка прав доступа."""
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]  # Регистрация открыта для всех
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsOwner]  # Только владелец может редактировать/удалять
        elif self.action == 'retrieve':
            permission_classes = [permissions.IsAuthenticated]  # Просмотр только авторизованным
        else:  # 'list'
            permission_classes = [permissions.IsAdminUser]  # Список только админам
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Получение информации о текущем пользователе."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def update_me(self, request):
        """Обновление информации о текущем пользователе."""
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterAPIView(generics.CreateAPIView):
    """Регистрация нового пользователя."""

    permission_classes = [permissions.AllowAny]
    serializer_class = UserCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            'user': UserSerializer(user, context=self.get_serializer_context()).data,
            'tokens': serializer.data['tokens'],
            'message': 'Пользователь успешно зарегистрирован'
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(generics.GenericAPIView):
    """Вход пользователя."""

    permission_classes = [permissions.AllowAny]
    serializer_class = UserLoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserSerializer(user, context=self.get_serializer_context()).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Успешный вход'
        })


class LogoutAPIView(generics.GenericAPIView):
    """Выход пользователя (блокировка refresh токена)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Успешный выход"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": "Неверный токен"}, status=status.HTTP_400_BAD_REQUEST)


class PaymentListAPIView(generics.ListAPIView):
    """Представление для получения списка платежей с фильтрацией."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ['payment_date', 'amount']
    ordering = ['-payment_date']

    def get_queryset(self):
        """Возвращаем платежи только текущего пользователя."""
        return Payment.objects.filter(user=self.request.user)


class UserPaymentsAPIView(generics.ListAPIView):
    """Получение платежей конкретного пользователя (только для админов или владельца)."""

    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ['payment_date', 'amount']

    def get_permissions(self):
        """Только админ или владелец может смотреть платежи."""
        if self.request.user.is_staff:
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [IsOwner]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Получаем платежи пользователя."""
        user_id = self.kwargs['user_id']
        return Payment.objects.filter(user_id=user_id)