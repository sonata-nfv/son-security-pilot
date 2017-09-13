all: run

dev:
	docker run -it --rm=true --link 'broker:broker' -v "$$(pwd)/test/:/squid-config/test/" -v "$$(pwd)/sonfsmvprxsquidconfiguration1/:/squid-config/sonfsmvprxsquidconfiguration1/" -v "$$(pwd)/ansible:/squid-config/ansible/"  -v '/var/run/docker.sock:/var/run/docker.sock' sonata-psa/dev-fsm /bin/bash

run:
	docker run -it --rm=true --link 'broker:broker' -v "$$(pwd)/test/:/squid-config/test/" -v "$$(pwd)/sonfsmvprxsquidconfiguration1/:/squid-config/sonfsmvprxsquidconfiguration1/" -v '/var/run/docker.sock:/var/run/docker.sock' sonata-psa/dev-fsm python test/testConf.py

build:
	docker build -t sonata-psa/dev-fsm .

broker:
	docker run -d --name broker rabbitmq:3-management
