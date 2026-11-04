FROM python:3.12-alpine

RUN apk add --no-cache tzdata \
 && pip install --no-cache-dir reportlab openpyxl requests websocket-client

COPY ha_doc.py ha_xlsx.py ha_changes.py ha_notes.py server.py /app/

WORKDIR /app
CMD ["python3", "-u", "server.py"]
