TARGET_DIR='/vpn-config'
SOURCE_DIR='vpn'

all: run

dev:
	docker run -it --rm=true --link 'broker:broker' -v "$$(pwd)/test/:$(TARGET_DIR)/test/" -v "$$(pwd)/$(SOURCE_DIR)/:$(TARGET_DIR)/$(SOURCE_DIR)/" -v "$$(pwd)/ansible:$(TARGET_DIR)/ansible/"  -v '/var/run/docker.sock:/var/run/docker.sock' sonata-psa/dev-fsm /bin/bash

run:
	docker run -it --rm=true --link 'broker:broker' -v "$$(pwd)/test/:$(TARGET_DIR)/test/" -v "$$(pwd)/$(SOURCE_DIR)/:$(TARGET_DIR)/$(SOURCE_DIR)/" -v '/var/run/docker.sock:/var/run/docker.sock' sonata-psa/dev-fsm python test/testConf.py

build:
	docker build -t sonata-psa/dev-fsm .

broker:
	docker run -d --name broker rabbitmq:3-management
