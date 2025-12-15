from django.urls import include, path
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('users.urls')),  # для приложения users
    path('lms/', include('lms.urls')),      # для приложения lms
]
