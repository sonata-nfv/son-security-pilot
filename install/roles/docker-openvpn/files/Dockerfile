FROM dperson/openvpn-client

RUN apt-get -y update && \
    apt-get -y install net-tools wget python3 runit easy-rsa && \
    mkdir -p /etc/service/openvpn && \
    touch /etc/service/openvpn/down

RUN sed -i -e 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' /etc/sysctl.conf && \
    # echo 1 > /proc/sys/net/ipv4/ip_forward && \
    cp -r /usr/share/easy-rsa/ /etc/openvpn && \
    mkdir /etc/openvpn/easy-rsa/keys && \
    sed -i -e 's/KEY_NAME="EasyRSA"/KEY_NAME="server"/' /etc/openvpn/easy-rsa/vars && \
    openssl dhparam -out /etc/openvpn/dh1024.pem 1024 && \
    ln -s /etc/openvpn/easy-rsa/openssl-1.0.0.cnf /etc/openvpn/easy-rsa/openssl.cnf && \
    cd /etc/openvpn/easy-rsa && . ./vars && \
    cd /etc/openvpn/easy-rsa && ./clean-all && \
    cd /etc/openvpn/easy-rsa && ./build-ca --batch && \
    cd /etc/openvpn/easy-rsa && ./build-key-server --batch server && \
    cp /etc/openvpn/easy-rsa/keys/server.crt /etc/openvpn/easy-rsa/keys/server.key /etc/openvpn/easy-rsa/keys/ca.crt /etc/openvpn && \
    cd /etc/openvpn/easy-rsa && ./build-key --batch client1 && \
    echo 'Done'

COPY ./run /etc/service/openvpn/

ENTRYPOINT ["/sbin/runit"]
