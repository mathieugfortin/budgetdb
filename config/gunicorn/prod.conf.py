# Django WSGI application path in pattern MODULE_NAME:VARIABLE_NAME
wsgi_app = "web_budget.wsgi:application"
# The granularity of Error log outputs
loglevel = "debug"
# The number of worker processes for handling requests
workers = 2
# The socket to bind
bind = "0.0.0.0:8005"
# Restart workers when code changes (development only!)
reload = True
# Write access and error info to /var/log
accesslog = "/app/logs/gunicorn/access.log"
# Error log - records Gunicorn server goings-on
errorlog = "/app/logs/gunicorn/error.log"
# Redirect stdout/stderr to log file
capture_output = True
# PID file so you can easily fetch process ID
pidfile = "/app/logs/gunicorn/gunicorn.pid"
# Daemonize the Gunicorn process (detach & enter background)
# daemon = True
daemon = False
