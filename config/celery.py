import os

from celery import Celery
from django.conf import settings

# Устанавливаем переменную окружения для настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Используем строку для конфигурации, чтобы не нужно было сериализовать объекты
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматическое обнаружение задач в приложениях Django
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Настройки для периодических задач (Celery Beat)
app.conf.beat_schedule = {
    'check-inactive-users-every-day': {
        'task': 'users.tasks.check_inactive_users',
        'schedule': 86400.0,  # Каждые 24 часа
    },
    'send-daily-statistics': {
        'task': 'lms.tasks.send_daily_statistics',
        'schedule': 86400.0,  # Каждые 24 часа
        'args': (),  # Дополнительные аргументы
    },
}

# Настройки timezone должны совпадать с Django
app.conf.timezone = settings.TIME_ZONE

# Опционально: настройки для результата задач
app.conf.result_backend = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
app.conf.result_expires = 3600  # Результаты хранятся 1 час

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')