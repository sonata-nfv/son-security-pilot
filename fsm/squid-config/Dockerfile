FROM python:3.4-slim
MAINTAINER SONATA

# configrurations
ENV mongo_host mongo
ENV mongo_port 27017
ENV broker_host amqp://guest:guest@broker:5672/%2F
ENV broker_exchange son-kernel

ENV SQUID_VERSION=3.3.8 \
    SQUID_CACHE_DIR=/var/spool/squid3 \
    SQUID_LOG_DIR=/var/log/squid3 \
    SQUID_USER=proxy

RUN apt-get clean \
    && apt-get update \
    && apt-get install -y git build-essential libffi-dev libssl-dev

RUN git clone --recursive https://github.com/sonata-nfv/son-sm.git
RUN git clone --recursive -b vpsa-install https://github.com/arocha7/son-security-pilot.git

WORKDIR /son-sm/son-mano-framework/son-mano-base
RUN python setup.py install

WORKDIR /son-sm/son-sm-template
RUN python setup.py install

WORKDIR /son-security-pilot/install/roles/docker-squid/files
COPY squid.conf /etc/squid3/squid.conf

ADD squid-config /squid-config

WORKDIR /squid-config
RUN python setup.py develop

#COPY deploy/vcdn/roles/files/entrypoint.sh /sbin/entrypoint.sh
RUN chmod 755 /sbin/entrypoint.sh

EXPOSE 3128/tcp
VOLUME ["${SQUID_CACHE_DIR}"]

CMD ["/sbin/entrypoint.sh"]
