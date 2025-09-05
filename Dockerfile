# Gunakan base image Python
FROM python:3.12-slim-bookworm

# ENV
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory di dalam container
WORKDIR /app

# Install dependencies untuk mysqlclient
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy semua file project ke dalam container
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Expose port Django
EXPOSE 8000

# Jalankan Gunicorn dengan gevent
CMD ["gunicorn", "webai.wsgi:application", "--bind", "0.0.0.0:8000", "--worker-class", "gevent"]