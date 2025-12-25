from django.http import HttpResponse
from django.urls import path

from .views import CreateCoursePaymentAPIView

urlpatterns = [
    path('create-payment/', CreateCoursePaymentAPIView.as_view(), name='create-payment'),
    path('success/', lambda request: HttpResponse('Payment successful!'), name='success'),
    path('cancel/', lambda request: HttpResponse('Payment canceled.'), name='cancel'),
]