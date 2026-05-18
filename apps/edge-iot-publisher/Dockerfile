FROM python:3.12-slim

WORKDIR /app
COPY edge_iot_publisher.py /app/edge_iot_publisher.py

USER 1000:1000
ENTRYPOINT ["python3", "/app/edge_iot_publisher.py", "--loop"]
