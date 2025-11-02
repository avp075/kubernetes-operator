FROM python:3.11-slim
WORKDIR /app
COPY name-space-operator.py /app/
RUN pip install --no-cache-dir kopf kubernetes
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["kopf", "run", "--standalone", "--verbose", "--all-namespaces", "/app/name-space-operator.py"]
#CMD ["kopf", "run", "--verbose", "name-space-operator.py"]
