FROM python:3.8-slim-buster

COPY ./app /

RUN pip3 install Flask \
      && pip3 install elasticsearch \
      && cd /

CMD [ "python3", "/app/main.py" ]