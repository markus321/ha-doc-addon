FROM python:3.12-alpine

RUN apk add --no-cache tzdata \
 && pip install --no-cache-dir reportlab requests websocket-client

COPY ha_doc.py server.py /app/

WORKDIR /app
CMD ["python3", "-u", "server.py"]
