FROM python:3.8.10-slim

WORKDIR /app

COPY ./app /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip && pip install -r requirements.txt

ENTRYPOINT ["/bin/bash", "run.sh"]