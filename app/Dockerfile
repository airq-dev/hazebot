# pull official base image
FROM python:3.8.1-slim-buster

RUN mkdir -p /home/app

RUN groupadd -r app && useradd -r app -g app

# set work directory
ENV HOME=/home/app
ENV APP_HOME=/home/app/app
RUN mkdir $APP_HOME
WORKDIR $APP_HOME

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
COPY install-deps.sh .
RUN chmod +x $APP_HOME/install-deps.sh
RUN ./install-deps.sh

RUN pip install --upgrade pip
COPY ./requirements.txt $APP_HOME/requirements.txt
RUN pip install -r requirements.txt

# copy project
COPY . $APP_HOME