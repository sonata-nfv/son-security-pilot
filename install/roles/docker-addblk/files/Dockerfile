FROM ubuntu:16.04

RUN apt-get update -y && \
    apt-get install -y runit squid wget net-tools inetutils-ping iptables && \
    mkdir -p /etc/squid /etc/service/squid && \
    wget -O /etc/squid/ad_block.txt "http://pgl.yoyo.org/adservers/serverlist.php?hostformat=nohtml&showintro=0&mimetype=plaintext" && \
    touch /etc/service/squid/down && \
    ln -sf /usr/share/doc/runit/debian /etc/runit && \
    chmod +x /etc/runit/* && \
    ln -sf /etc/service /service

COPY ./run /etc/service/squid/

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
