FROM ubuntu:16.04

RUN sed -i 's/archive/fr.archive/g' /etc/apt/sources.list && \
    apt-get update -y && \
    apt-get install -y runit squid wget net-tools inetutils-ping iptables python3 dnsmasq && \
    mkdir -p /etc/squid /etc/service/squid && \
    wget -O /etc/squid/ad_block.txt "https://pgl.yoyo.org/adservers/iplist.php?format=iptables&showintro=0&mimetype=plaintext" && \
    touch /etc/service/squid/down && \
    ln -sf /usr/share/doc/runit/debian /etc/runit && \
    chmod +x /etc/runit/* && \
    ln -sf /etc/service /service

RUN wget -O /etc/dnsmasq.d/ad_block.conf "https://pgl.yoyo.org/adservers/serverlist.php?hostformat=dnsmasq&showintro=1&mimetype=plaintext" && \
    mkdir -p /etc/service/dnsmasq && \
    touch /etc/service/dnsmasq/down

COPY ./run /etc/service/squid/
COPY ./dnsmasq.conf /etc/
COPY ./run-dnsmasq /etc/service/dnsmasq/run

ENTRYPOINT ["/sbin/runit"]

# FROM sameersbn/squid

# RUN apt-get update -y && \
#     apt-get install -y runit && \
#     mkdir -p /etc/squid /etc/service/squid && \
#     wget -O /etc/squid/ad_block.txt "http://pgl.yoyo.org/adservers/serverlist.php?hostformat=nohtml&showintro=0&mimetype=plaintext" && \
#     touch /etc/service/squid/down && \
#     ln -sf /usr/share/doc/runit/debian /etc/runit && \
#     chmod +x /etc/runit/* && \
#     ln -sf /etc/service /service
# #sed -i 's~/service~/etc/service~' /etc/runit/2

# COPY ./run /etc/service/squid/

# ENTRYPOINT ["/sbin/runit"]
