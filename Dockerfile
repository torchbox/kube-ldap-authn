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

COPY . /app

ENV FLASK_APP /app/app.py
CMD [ "flask", "run" ]
