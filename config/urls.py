from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView


# Ленивые импорты, чтобы избежать ошибок
def get_router():
    from lms.views import CourseViewSet
    from users.views import UserViewSet

    router = DefaultRouter()
    router.register(r'courses', CourseViewSet, basename='course')
    router.register(r'users', UserViewSet, basename='user')
    return router


urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Auth endpoints
    path('api/register/', include('users.auth_urls')),
    path('api/auth/', include('users.auth_urls')),

    # API endpoints
    path('api/', include((get_router().urls, 'api'))),
    path('api/lessons/', include('lms.urls')),
    path('api/payments/', include('users.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)