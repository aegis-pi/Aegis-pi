FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY edge_iot_publisher.py /app/edge_iot_publisher.py

USER 1000:1000
ENTRYPOINT ["python3", "/app/edge_iot_publisher.py", "--loop"]
