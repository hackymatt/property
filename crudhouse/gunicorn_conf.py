import multiprocessing

# Django WSGI application path in pattern MODULE_NAME:VARIABLE_NAME
wsgi_app = "core.wsgi"
# The number of worker processes for handling requests
workers = multiprocessing.cpu_count() * 3 + 1
# Timeout
timeout = 30
# The socket to bind
bind = "0.0.0.0:8000"
# Daemonize the Gunicorn process (detach & enter background)
daemon = False
