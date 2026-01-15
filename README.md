# Learning Management System (LMS)

Проект системы управления обучением, развернутый с использованием Docker и CI/CD.

## Быстрый старт

### Предварительные требования
- Docker 20.10+
- Docker Compose 1.29+
- Git

## Локальный запуск

1. Клонируйте репозиторий:
```bash
git clone https://github.com/ваш-username/lms.git
cd lms
```

2. Создайте файл .env на основе .env.example:

```
cp .env.example .env
```

3. Запустите приложение:
```
docker-compose up -d
```

4. Приложение будет доступно по адресу:\
Frontend: http://localhost\
API: http://localhost:8000/api/ \
Admin: http://localhost:8000/admin/


## Настройка окружения

Отредактируйте .env файл:

### Django
SECRET_KEY=ваш-secret-key
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,ваш-домен.ru

####База данных
```DB_NAME=lms
DB_USER=lmsuser
DB_PASSWORD=ваш-пароль
```

### Redis
```REDIS_URL=redis://redis:6379/0```

### Внешние сервисы
```STRIPE_PUBLISHABLE_KEY=pk_...
STRIPE_SECRET_KEY=sk_...
BASE_URL=https://ваш-домен.ru
```

## Docker команды
### Основные команды
```
# Запуск
docker-compose up -d

# Остановка
docker-compose down

# Просмотр логов
docker-compose logs -f web
docker-compose logs -f celery-worker

# Пересборка
docker-compose up -d --build

# Выполнение команд в контейнере
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## Управление данными
```
# Бэкап базы данных
docker-compose exec db pg_dump -U lmsuser lms > backup.sql

# Восстановление
cat backup.sql | docker-compose exec -T db psql -U lmsuser lms
```

## Деплой на сервер

### Требования к серверу
```
Ubuntu 20.04+
Docker & Docker Compose
Nginx (устанавливается автоматически)
Domain name с настроенными DNS
```

## Автоматический деплой

Настройте secrets в GitHub:

SERVER_HOST - IP адрес сервера \
SERVER_USER - пользователь сервера \
SSH_PRIVATE_KEY - приватный SSH ключ \
Все переменные из .env.example \
При push в ветку main произойдет автоматический деплой

## Ручной деплой
```
# На сервере
git clone https://github.com/ваш-username/lms.git
cd lms

# Настройка окружения
nano .env

# Запуск
docker-compose up -d
```


## CI/CD Pipeline

Процесс включает:

Тестирование - unit tests, интеграционные тесты \
Линтинг - flake8, black \
Сборка Docker - мульти-архитектурная сборка \
Деплой - автоматический на production сервер \
Workflow файлы


.github/workflows/deploy.yml - основной CI/CD pipeline

Запускается при push в main/master

## Структура проекта


lms/ \
├── config/              # Django проект \
├── apps/               # Django приложения \
├── nginx/              # Nginx конфигурация \
├── docker-compose.yml  # Docker Compose \
├── Dockerfile          # Docker образ Django \
├── requirements.txt    # Python зависимости \
├── .env.example        # Шаблон переменных окружения \
└── .github/workflows/  # CI/CD конфигурация

## Разработка

### Локальная разработка
```
# Установка зависимостей
pip install -r requirements.txt

# Запуск миграций
python manage.py migrate

# Запуск сервера разработки
python manage.py runserver
```

## Тестирование
```
bash
# Запуск всех тестов
pytest

# Тесты с покрытием
pytest --cov=.

# Запуск линтера
flake8 .
black --check .
```

## Безопасность

### Производственные настройки

```DEBUG=False
Настроены ALLOWED_HOSTS
HTTPS через Nginx
Защищенные заголовки
Отдельный пользователь в Docker
Обновление зависимостей
```


## Обновление Python пакетов
```
pip freeze > requirements.txt
```

## Проверка уязвимостей
```pip-audit```

## Поддержка

### Мониторинг

Логи доступны через docker-compose logs \
Health check: http://ваш-домен/health/ \
Статус контейнеров: docker-compose ps \

### Устранение неполадок

```
# Проверка статуса
docker-compose ps
docker-compose logs

# Перезапуск сервиса
docker-compose restart web

# Очистка
docker system prune -a
```
 
## Лицензия

MIT License

