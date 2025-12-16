from rest_framework import viewsets, generics
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from .models import User, Payment
from .serializers import UserSerializer, PaymentSerializer
from .filters import PaymentFilter


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с пользователями (CRUD)."""

    queryset = User.objects.all()
    serializer_class = UserSerializer


class PaymentListAPIView(generics.ListAPIView):
    """Представление для получения списка платежей с фильтрацией."""

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PaymentFilter

    # Поля для сортировки
    ordering_fields = ['payment_date', 'amount']
    ordering = ['-payment_date']  # Сортировка по умолчанию