# Gunicorn configuration file
bind = "0.0.0.0:10000"
# Conservative settings for small Railway dynos: one worker, two threads
workers = 1
threads = 2
timeout = 90
graceful_timeout = 30
keepalive = 15
preload_app = False