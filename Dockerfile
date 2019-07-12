FROM python:3.6-alpine

WORKDIR /workspace

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY prom-redis-exporter.py /usr/bin/

ENV PYTHONUNBUFFERED 1
STOPSIGNAL SIGINT
CMD ["prom-redis-exporter.py"]
