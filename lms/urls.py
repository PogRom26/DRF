from django.urls import path
from .views import (
    LessonListCreateAPIView, LessonRetrieveUpdateDestroyAPIView,
    SubscriptionAPIView, CourseSubscriptionAPIView
)

urlpatterns = [
    path('', LessonListCreateAPIView.as_view(), name='lesson-list'),
    path('<int:pk>/', LessonRetrieveUpdateDestroyAPIView.as_view(), name='lesson-detail'),
    path('subscriptions/', SubscriptionAPIView.as_view(), name='subscription-list'),
    path('subscriptions/<int:course_id>/', CourseSubscriptionAPIView.as_view(), name='course-subscription'),
]