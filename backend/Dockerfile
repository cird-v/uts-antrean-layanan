FROM python:3.12-slim

ARG APP_VERSION=dev
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATA_DIR=/var/lib/backend_data \
    APP_VERSION=${APP_VERSION}

WORKDIR /app
COPY app.py .

# Folder data -> di-mount oleh Named Volume `queue-db-data`
RUN mkdir -p /var/lib/backend_data
VOLUME ["/var/lib/backend_data"]

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

CMD ["python", "app.py"]
