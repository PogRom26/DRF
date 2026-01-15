from django.urls import path

from .views import (
    CreateStripePaymentForCourseAPIView,
    PaymentCreateAPIView,
    PaymentListAPIView,
    PaymentRetrieveAPIView,
    StripePaymentStatusAPIView,
    UserPaymentsAPIView,
)

urlpatterns = [
    # Основные эндпоинты платежей
    path("", PaymentListAPIView.as_view(), name="payment-list"),
    path("create/", PaymentCreateAPIView.as_view(), name="payment-create"),
    path("<int:pk>/", PaymentRetrieveAPIView.as_view(), name="payment-detail"),
    # Stripe-specific эндпоинты
    path(
        "<int:payment_id>/stripe-status/",
        StripePaymentStatusAPIView.as_view(),
        name="stripe-payment-status",
    ),
    path(
        "course/<int:course_id>/stripe-payment/",
        CreateStripePaymentForCourseAPIView.as_view(),
        name="create-stripe-payment-course",
    ),
    # Эндпоинт платежей пользователя (для админов)
    path("user/<int:user_id>/", UserPaymentsAPIView.as_view(), name="user-payments"),
]
