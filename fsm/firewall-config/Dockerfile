FROM python:3.5-slim
MAINTAINER SONATA

# configrurations
ENV mongo_host mongo
ENV mongo_port 27017
ENV broker_host amqp://guest:guest@broker:5672/%2F
ENV broker_exchange son-kernel


RUN apt-get update && apt-get -y install python3-pip ssh \
    && apt-get update && pip3 install paramiko && pip3 install ansible \
    && apt-get install -y python3-amqp python3-amqplib

ADD son-sm/son-mano-framework/son-mano-base /son-mano-base
ADD son-sm/son-sm-template /son-sm-template


WORKDIR /son-mano-base
Run python setup.py install

WORKDIR /son-sm-template
RUN python setup.py install

WORKDIR /
ADD fsm/firewall-config /firewall-config

WORKDIR /firewall-config
RUN python setup.py develop

CMD ["firewall-config"]

