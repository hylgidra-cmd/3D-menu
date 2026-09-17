FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

# Render routes public traffic to the port exposed by the Docker image.  Its
# Web Service runtime sets PORT=10000, so exposing 8000 leaves gunicorn healthy
# internally while every external request waits on the wrong port.
EXPOSE 10000

ENTRYPOINT ["./entrypoint.sh"]
