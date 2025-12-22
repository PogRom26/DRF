from django.urls import path
from .views import PaymentListAPIView, UserPaymentsAPIView

urlpatterns = [
    path('', PaymentListAPIView.as_view(), name='payment-list'),
    path('user/<int:user_id>/', UserPaymentsAPIView.as_view(), name='user-payments'),
]