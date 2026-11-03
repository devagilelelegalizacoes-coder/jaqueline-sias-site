"""Configuração do Gunicorn (produção)."""
import multiprocessing
import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("GUNICORN_WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 4)))
threads = int(os.getenv("GUNICORN_THREADS", "2"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 20
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "*")
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
# Não registra query strings (podem conter dados pessoais)
access_log_format = '%(h)s "%(m)s %(U)s %(H)s" %(s)s %(b)s %(L)ss'
