# Copyright (c) 2015 SONATA-NFV
# ALL RIGHTS RESERVED.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#    http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# Neither the name of the SONATA-NFV [, ANY ADDITIONAL AFFILIATION]
# nor the names of its contributors may be used to endorse or promote
# products derived from this software without specific prior written
# permission.
# This work has been performed in the framework of the SONATA project,
# funded by the European Commission under Grant number 671517 through
# the Horizon 2020 and 5G-PPP programmes. The authors would like to
# acknowledge the contributions of their colleagues of the SONATA
# partner consortium (www.sonata-nfv.eu).

FROM python:3.5-slim
MAINTAINER SONATA

ENV broker_host amqp://guest:guest@broker:5672/%2F
ENV broker_exchange son-kernel

# install package dependencies
RUN apt-get clean \
    && apt-get update \
    # build-essential libffi-dev  
    && apt-get install -y wget git libssl-dev \
    && wget https://download.docker.com/linux/static/stable/x86_64/docker-17.06.2-ce.tgz \
    && tar -xzf docker-*-ce.tgz \
    && cp docker/docker /usr/bin/ \
    && rm -rf docker-*-ce.tgz docker \
    && pip install --no-cache-dir paramiko ansible \
#    && pip install --no-cache-dir 'ansible<=2.3.2.0' docker \
#    && pip install paramiko \
#    && sed -i 's/def __init__(self, verbosity=0)/def __init__(self, verbosity=4)/' '/usr/local/lib/python3.5/site-packages/ansible/utils/display.py' \
    && apt-get clean

# clone son-sm repo to install dependencies, then install fsm dependencies (sonsmbase and sonmanobase)
RUN git clone --recursive https://github.com/sonata-nfv/son-sm.git \
    && cd /son-sm/son-mano-framework/son-mano-base \
    && python setup.py install \
    && cd /son-sm/son-sm-template \
    && python setup.py install

COPY firewall-config/ /firewall-config
COPY vpn-config/ /vpn-config
COPY squid-config/ /cache-config

RUN cd /firewall-config \
    && python setup.py develop \
    && cd /vpn-config \
    && python setup.py develop \
    && cd /cache-config \
    && python setup.py develop

CMD ["/bin/bash"]

