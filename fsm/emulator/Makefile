VPN_VOLUMES=-v "$$(pwd)/vpn-config/test/:/vpn-config/test/" -v "$$(pwd)/vpn-config/vpn_css/:/vpn-config/vpn_css/" -v "$$(pwd)/vpn-config/ansible:/vpn-config/ansible/"
FIREWALL_VOLUMES=-v "$$(pwd)/firewall-config/firewall:/firewall-config/firewall" -v "$$(pwd)/firewall-config/ansible:/firewall-config/ansible" 
EMULATOR_VOLUMES=-v "$$(pwd)/emulator/:/emulator/"

EMULATOR_DOCKER_CMD=cd .. && docker run -it --rm=true --link 'broker:broker' --env 'SON_EMULATOR=1' \
  ${VPN_VOLUMES} \
  ${FIREWALL_VOLUMES} \
  ${EMULATOR_VOLUMES} \
  -v '/var/run/docker.sock:/var/run/docker.sock' \
  sonata-psa/dev-fsm-emulator


all: run

dev:
	cd .. && docker run -it --rm=true --link 'broker:broker' --env 'SON_EMULATOR=1' \
	  ${VPN_VOLUMES} \
	  ${FIREWALL_VOLUMES} \
	  ${EMULATOR_VOLUMES} \
	  -v '/var/run/docker.sock:/var/run/docker.sock' \
	  sonata-psa/dev-fsm-emulator

run:
	${EMULATOR_DOCKER_CMD} python --help

broker:
	docker run -d --name broker rabbitmq:3-management

build:
	cd .. && docker build -f emulator/Dockerfile -t sonata-psa/dev-fsm-emulator .
