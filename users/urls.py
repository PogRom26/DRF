from django.urls import path
from .views import PaymentListAPIView

urlpatterns = [
    path('', PaymentListAPIView.as_view(), name='payment-list'),
]