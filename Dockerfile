FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py vdot.py database.py garmin_sync.py ./
EXPOSE 5000
# Laduj .env z /data/bieganie/.env jesli istnieje
CMD ["sh", "-c", "test -f /data/bieganie/.env && export $(grep -v '^#' /data/bieganie/.env | xargs) 2>/dev/null; exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --preload server:app"]
