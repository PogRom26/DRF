# Dockerfile
FROM python:3.12-slim as builder

# Установка системных зависимостей для сборки
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Финальный образ
FROM python:3.12-slim

# Установка рантайм зависимостей
RUN apt-get update && apt-get install -y \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя
RUN useradd -m -u 1000 django

WORKDIR /app

# Копирование зависимостей из builder
COPY --from=builder /root/.local /home/django/.local
ENV PATH=/home/django/.local/bin:$PATH

# Копирование проекта
COPY --chown=django:django . .

# Создание директорий
RUN mkdir -p /app/static /app/media /app/logs \
    && chown -R django:django /app \
    && chmod 755 /app /app/logs

USER django

# Порт
EXPOSE 8000

# Команда запуска
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-"]