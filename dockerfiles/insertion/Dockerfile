###########
# BUILDER #
###########

# pull official base image
FROM ubuntu:18.04 as builder

ENV DEBIAN_FRONTEND=noninteractive

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies
RUN apt update \
    && apt-get install build-essential -y

RUN apt update -y && apt install -y libpq-dev

RUN apt-get update \
  && apt-get install -y python3-pip python3-dev \
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip

# install dependencies
COPY ./requirements.txt .
RUN cat requirements.txt | xargs -n 1 -L 1 pip3 wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels


#########
# FINAL #
#########

# pull official base image
FROM ubuntu:18.04

ENV DEBIAN_FRONTEND=noninteractive

# install python (optimize this part with builder)
RUN apt-get update \
  && apt-get install -y python3-pip python3-dev python3-opencv \
  && cd /usr/local/bin \
  && ln -s /usr/bin/python3 python \
  && pip3 install --upgrade pip

# install dependencies
RUN apt update -y && apt install -y libpq-dev
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .
RUN pip install --no-cache /wheels/*

# create directory for the app user and create the app user
RUN mkdir -p /app 
# && useradd app

# create the appropriate directories
ENV HOME=/app
ENV APP_HOME=/app/insert_to_db
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

COPY . $APP_HOME


