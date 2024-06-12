FROM python:3.8-alpine

WORKDIR /workspace

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY prom_redis_exporter/prom_redis_exporter.py /usr/bin/

ENV PYTHONUNBUFFERED 1
STOPSIGNAL SIGINT
CMD ["prom_redis_exporter.py"]
