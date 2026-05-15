FROM python:3.13-alpine

WORKDIR /app

RUN addgroup -S aegis && adduser -S -G aegis -u 10001 aegis

COPY edge_agent.py /app/edge_agent.py

ENV AEGIS_FACTORY_ID=factory-a \
    AEGIS_HTTP_PORT=8080 \
    PYTHONUNBUFFERED=1

USER aegis

EXPOSE 8080

CMD ["python", "/app/edge_agent.py"]

