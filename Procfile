web: gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers 1 --worker-class sync --timeout 180 --max-requests 10 --max-requests-jitter 5
