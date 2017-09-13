FROM python:3.5-slim
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

RUN apt-get update \
    && apt-get install -y wget git build-essential libffi-dev libssl-dev \
    && wget https://download.docker.com/linux/static/stable/x86_64/docker-17.06.2-ce.tgz \
    && tar -xzf docker-*-ce.tgz \
    && cp docker/docker /usr/bin/ \
    && rm -rf docker-*-ce.tgz docker \
    && pip install --no-cache-dir ansible docker \
    && sed -i 's/def __init__(self, verbosity=0)/def __init__(self, verbosity=4)/' '/usr/local/lib/python3.5/site-packages/ansible/utils/display.py' \
    && apt-get clean

RUN git clone --recursive https://github.com/sonata-nfv/son-sm.git
RUN git clone --recursive -b vpsa-install https://github.com/arocha7/son-security-pilot.git

WORKDIR /son-sm/son-mano-framework/son-mano-base
RUN python setup.py install

WORKDIR /son-sm/son-sm-template
RUN python setup.py install

WORKDIR /son-security-pilot/install/roles/docker-squid/files

COPY . /squid-config/

WORKDIR /squid-config
RUN python setup.py develop

#COPY deploy/vcdn/roles/files/entrypoint.sh /sbin/entrypoint.sh
RUN chmod 755 ./ansible/roles/squid/files/entrypoint.sh

EXPOSE 3128/tcp
VOLUME ["${SQUID_CACHE_DIR}"]

CMD ["./ansible/roles/squid/files/entrypoint.sh"]
