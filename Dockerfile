FROM python:3.11.0-alpine
WORKDIR /app
ADD requirements.txt /app

ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

ADD . /app

ENTRYPOINT ["python", "bot.py"]
