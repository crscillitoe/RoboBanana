FROM python:3

RUN apt-get -qq update && apt-get -qq install sqlite3 -y

RUN mkdir /var/raffle_bot
WORKDIR /var/raffle_bot

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ARG DB_PATH
RUN mkdir -p $(dirname $DB_PATH)
RUN touch $DB_PATH
RUN sqlite3 $DB_PATH < ./raffle.db.schema

CMD [ "python", "-u", "./bot.py" ]
