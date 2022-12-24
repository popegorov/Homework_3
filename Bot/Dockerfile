FROM python:latest

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip3 install -r requirements.txt

COPY ./main.py /usr/src/app
COPY ./bot.py /usr/src/app
COPY ./dto.py /usr/src/app
COPY ./game_async_engine.py /usr/src/app
COPY ./game_dao.py /usr/src/app
COPY ./init_db.py /usr/src/app

RUN python3 init_db.py

EXPOSE 8888
CMD ["python3", "main.py"]
