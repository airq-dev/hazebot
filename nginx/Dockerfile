FROM nginx:1.17-alpine

ARG CONF_FILE=nginx.conf

RUN rm /etc/nginx/conf.d/default.conf
COPY $CONF_FILE /etc/nginx/conf.d
COPY html /etc/nginx/html
