FROM simiprambos/pychrome:latest

LABEL maintainer="simi.prambos@gmail.com"

ENV APP_HOME /usr/src/app
WORKDIR /$APP_HOME

COPY . $APP_HOME/

RUN pip3 install -r requirement.txt

RUN mkdir static && mkdir media

CMD tail -f /dev/null