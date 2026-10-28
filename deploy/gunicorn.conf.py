# Start from the repository root: gunicorn -c deploy/gunicorn.conf.py byte_project.wsgi
bind = '127.0.0.1:8000'
workers = 2
worker_class = 'sync'
timeout = 120
graceful_timeout = 120
max_requests = 500
max_requests_jitter = 50
limit_request_line = 4094
limit_request_fields = 60
limit_request_field_size = 4094
accesslog = '-'
errorlog = '-'
forwarded_allow_ips = '127.0.0.1'
