# Copyright (c) 2017 Torchbox Ltd.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely. This software is provided 'as-is', without any express or implied
# warranty.

FROM python:3.6.1

RUN apt-get update && apt-get -qy install libldap2-dev libsasl2-dev

COPY requirements.txt /
RUN pip install -r /requirements.txt

WORKDIR /app
COPY app.py .

ENV FLASK_APP /app/app.py
ENV PYTHONPATH /app
CMD [ "uwsgi", "--master", "--disable-logging", "--workers=2", "--http-socket=:8087", "--module=app:app" ]
