FROM python:3.11.1

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install python-telegram-bot --pre --upgrade
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src .

CMD [ "python", "./main.py" ]