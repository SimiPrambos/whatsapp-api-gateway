FROM simiprambos/pychrome:latest

LABEL maintainer="simi.prambos@gmail.com"

ENV APP_HOME /usr/src/app
WORKDIR /$APP_HOME

COPY . $APP_HOME/

CMD tail -f /dev/null