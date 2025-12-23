from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import Payment
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    UserLoginSerializer, PaymentSerializer
)
from .filters import PaymentFilter
from .permissions import IsOwner, IsNotModerator

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
            # Список пользователей доступен только админам и модераторам
            permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser | IsNotModerator]
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

        # Автоматически добавляем нового пользователя в группу студентов
        students_group, created = Group.objects.get_or_create(name='students')
        user.groups.add(students_group)

        return Response({
            'user': UserSerializer(user, context=self.get_serializer_context()).data,
            'tokens': serializer.data['tokens'],
            'message': 'Пользователь успешно зарегистрирован и добавлен в группу студентов'
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
        if self.request.user.is_staff or self.request.user.groups.filter(name='moderators').exists():
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsOwner]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Получаем платежи пользователя."""
        user_id = self.kwargs['user_id']
        return Payment.objects.filter(user_id=user_id)


from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from .models import Payment, User
from .serializers import PaymentSerializer
from .filters import PaymentFilter
from lms.stripe_service import StripeService
from lms.models import Course, Lesson
import logging

logger = logging.getLogger(__name__)


class PaymentCreateAPIView(generics.CreateAPIView):
    """API для создания платежей с интеграцией Stripe."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentSerializer

    def perform_create(self, serializer):
        """Переопределяем создание платежа для интеграции с Stripe."""
        # Сохраняем платеж с пользователем
        payment = serializer.save(user=self.request.user)

        # Если выбран способ оплаты Stripe, создаем сессию в Stripe
        if payment.payment_method == 'stripe':
            try:
                stripe_service = StripeService()

                # Определяем, что оплачивается: курс или урок
                if payment.course:
                    # Создаем платеж в Stripe для курса
                    stripe_result = stripe_service.create_payment_for_course(
                        course_title=payment.course.title,
                        course_description=payment.course.description or '',
                        price_amount=payment.price,  # Используем цену из платежа
                        user_id=payment.user.id,
                        user_email=payment.user.email,
                        course_id=payment.course.id,
                        currency='usd'
                    )
                elif payment.lesson:
                    # Создаем платеж в Stripe для урока
                    stripe_result = stripe_service.create_payment_for_lesson(
                        lesson_title=payment.lesson.title,
                        lesson_description=payment.lesson.description or '',
                        price_amount=payment.price,  # Используем цену из платежа
                        user_id=payment.user.id,
                        user_email=payment.user.email,
                        lesson_id=payment.lesson.id,
                        currency='usd'
                    )
                else:
                    # Ни курс, ни урок не указаны
                    raise ValueError("Для оплаты через Stripe необходимо указать курс или урок")

                if stripe_result['success']:
                    # Обновляем платеж данными из Stripe
                    payment.stripe_product_id = stripe_result.get('product_id')
                    payment.stripe_price_id = stripe_result.get('price_id')
                    payment.stripe_session_id = stripe_result.get('session_id')
                    payment.stripe_payment_url = stripe_result.get('payment_url')
                    payment.payment_status = 'pending'
                    payment.save()

                    logger.info(f"Stripe payment created for payment {payment.id}")
                else:
                    # Ошибка при создании платежа в Stripe
                    error_msg = stripe_result.get('error', 'Неизвестная ошибка Stripe')
                    logger.error(f"Stripe payment creation failed: {error_msg}")
                    # Можно поднять исключение или оставить платеж без Stripe данных

            except Exception as e:
                logger.error(f"Error integrating Stripe for payment {payment.id}: {str(e)}")
                # Платеж сохраняется, но без данных Stripe


class PaymentRetrieveAPIView(generics.RetrieveAPIView):
    """Представление для получения деталей платежа."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        """Возвращаем платежи только текущего пользователя."""
        return Payment.objects.filter(user=self.request.user)


class StripePaymentStatusAPIView(APIView):
    """API для проверки статуса платежа Stripe."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, payment_id):
        """Проверяет статус платежа Stripe."""
        payment = get_object_or_404(Payment, id=payment_id, user=request.user)

        if not payment.stripe_session_id:
            return Response({
                'error': 'Этот платеж не связан с Stripe'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            stripe_service = StripeService()
            session_result = stripe_service.retrieve_session(payment.stripe_session_id)

            if session_result['success']:
                # Обновляем статус платежа
                stripe_status = session_result['payment_status']

                # Маппим статусы Stripe на наши статусы
                status_mapping = {
                    'paid': 'succeeded',
                    'unpaid': 'pending',
                    'no_payment_required': 'succeeded'
                }

                payment.payment_status = status_mapping.get(stripe_status, 'pending')
                payment.save()

                return Response({
                    'payment_id': payment.id,
                    'stripe_session_id': payment.stripe_session_id,
                    'payment_status': payment.payment_status,
                    'stripe_status': stripe_status,
                    'payment_url': payment.stripe_payment_url,
                    'amount': str(payment.amount),
                    'message': f"Статус платежа: {payment.payment_status}"
                })
            else:
                return Response({
                    'error': session_result.get('error', 'Ошибка при проверке статуса Stripe')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Error checking Stripe payment status: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateStripePaymentForCourseAPIView(APIView):
    """API для создания платежа Stripe для существующего курса."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, course_id):
        """Создает платеж Stripe для указанного курса."""
        course = get_object_or_404(Course, id=course_id)
        user = request.user

        # Проверяем, не оплачен ли уже курс
        existing_payment = Payment.objects.filter(
            user=user,
            course=course,
            payment_status='succeeded'
        ).first()

        if existing_payment:
            return Response({
                'success': True,
                'message': 'Курс уже оплачен',
                'payment_id': existing_payment.id,
                'already_paid': True
            })

        # Получаем цену из запроса или используем стандартную
        price_amount = request.data.get('price', 100.00)

        try:
            stripe_service = StripeService()

            # Создаем платеж в Stripe
            stripe_result = stripe_service.create_payment_for_course(
                course_title=course.title,
                course_description=course.description or '',
                price_amount=price_amount,
                user_id=user.id,
                user_email=user.email,
                course_id=course.id,
                currency='usd'
            )

            if not stripe_result['success']:
                return Response({
                    'success': False,
                    'error': stripe_result.get('error', 'Ошибка при создании платежа Stripe')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Создаем запись платежа в нашей системе
            payment = Payment.objects.create(
                user=user,
                course=course,
                price=price_amount,
                amount=price_amount,
                payment_method='stripe',
                stripe_product_id=stripe_result.get('product_id'),
                stripe_price_id=stripe_result.get('price_id'),
                stripe_session_id=stripe_result.get('session_id'),
                stripe_payment_url=stripe_result.get('payment_url'),
                payment_status='pending'
            )

            return Response({
                'success': True,
                'payment_id': payment.id,
                'payment_url': payment.stripe_payment_url,
                'session_id': payment.stripe_session_id,
                'price': str(payment.price),
                'message': 'Платежная сессия Stripe создана. Перейдите по ссылке для оплаты.'
            })

        except Exception as e:
            logger.error(f"Error creating Stripe payment for course: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserPaymentsAPIView(generics.ListAPIView):
    """Получение платежей конкретного пользователя (только для админов или владельца)."""

    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ['payment_date', 'amount']

    def get_permissions(self):
        """Только админ или владелец может смотреть платежи."""
        if self.request.user.is_staff or self.request.user.groups.filter(name='moderators').exists():
            permission_classes = [permissions.IsAuthenticated]
        else:
            # Проверяем, что пользователь запрашивает свои платежи
            from ..permissions import IsOwner
            permission_classes = [IsOwner]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Получаем платежи пользователя."""
        user_id = self.kwargs['user_id']
        return Payment.objects.filter(user_id=user_id)