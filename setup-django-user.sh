#!/bin/bash
# setup-django-user.sh

set -e

echo "=== Настройка окружения пользователя django ==="

# Переключение на пользователя django
sudo -u django bash << 'EOF'

# Создание директории проекта
mkdir -p ~/projects/lms
cd ~/projects/lms

# Клонирование проекта (если нужно)
# git clone <ваш-репозиторий> .

# Создание виртуального окружения
python3.11 -m venv venv
source venv/bin/activate

# Создание структуры директорий
mkdir -p logs media static db backups

# Создание .env файла
cat > .env << 'ENVEOF'
# Django
SECRET_KEY='your-production-secret-key-change-this'
DEBUG=False
ALLOWED_HOSTS=ваш-домен.ru,www.ваш-домен.ru,localhost,127.0.0.1,ваш_IP
BASE_URL=https://ваш-домен.ru

# Database
DATABASE_URL=sqlite:///db/production.db

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=ваш-email@gmail.com
EMAIL_HOST_PASSWORD=ваш-пароль-приложения
DEFAULT_FROM_EMAIL=ваш-email@gmail.com

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_test_ваш_ключ
STRIPE_SECRET_KEY=sk_test_ваш_ключ
STRIPE_WEBHOOK_SECRET=whsec_ваш_ключ

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TIMEZONE=Europe/Moscow

# Application
NOTIFICATION_HOURS_THRESHOLD=4
INACTIVE_DAYS_THRESHOLD=30
ENVEOF

echo "=== Окружение настроено ==="

EOF