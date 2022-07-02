FROM python:3.10-slim

WORKDIR /app
ADD . /app
RUN pip3 install absl-py google-cloud-pubsub requests

ENTRYPOINT ["python3", "/app/main.py"]
