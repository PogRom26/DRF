#!/bin/bash
# setup-server.sh

set -e

echo "=== Настройка сервера для DRF проекта ==="

# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nginx \
    redis-server \
    git \
    curl \
    supervisor \
    certbot \
    python3-certbot-nginx \
    ufw \
    fail2ban \
    htop \
    tree \
    sqlite3

# Настройка firewall
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

# Настройка часового пояса
sudo timedatectl set-timezone Europe/Moscow

# Настройка Redis
sudo sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf
sudo systemctl restart redis
sudo systemctl enable redis

# Создание пользователя для приложения
sudo adduser --disabled-password --gecos "" django
sudo usermod -aG sudo django

echo "=== Базовая настройка завершена ==="