FROM python:3.11.0-alpine3.15

# Create user
RUN adduser -D daikin

WORKDIR /app
COPY src/requirements.txt .

# Install required modules and Speedtest CLI
RUN pip install --no-cache-dir -r requirements.txt

COPY src/. .

USER daikin

CMD ["python", "-u", "exporter.py"]

HEALTHCHECK --timeout=10s CMD wget --no-verbose --tries=1 --spider http://localhost:${DAIKIN_EXPORTER_PORT:=5555}/
