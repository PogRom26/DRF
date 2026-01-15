import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 2
max_requests = 1000
max_requests_jitter = 50
timeout = 120
keepalive = 5

# Логирование
accesslog = "/home/django/lms-project/logs/gunicorn.access.log"
errorlog = "/home/django/lms-project/logs/gunicorn.error.log"
loglevel = "info"

# Безопасность
forwarded_allow_ips = "127.0.0.1"
proxy_allow_ips = "127.0.0.1"
