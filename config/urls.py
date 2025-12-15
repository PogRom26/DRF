from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter


# Ленивые импорты, чтобы избежать ошибок
def get_router():
    from lms.views import CourseViewSet
    from users.views import UserViewSet

    router = DefaultRouter()
    router.register(r'courses', CourseViewSet)
    router.register(r'users', UserViewSet)
    return router


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include((get_router().urls, 'api'))),
    path('api/lessons/', include('lms.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)