FROM python:3.10-slim-bullseye

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

ENV BOT_TOKEN ""
CMD [ "python3", "./main.py" ]

