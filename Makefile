all: package package-emu

docker-images: docker-image-squid docker-image-fw

docker-image-squid:
	cd install/roles/docker-squid/files && \
	  docker build -t sonata-psa/squid .

docker-image-haproxy:
	cd install/roles/docker-haproxy/files && \
	  docker build -t sonata-psa/haproxy .

# docker-image-snort:
# 	docker pull glanf/snort

docker-image-vpn:
	cd install/roles/docker-openvpn/files && \
		docker build -t sonata-psa/vpn .

docker-image-fw:
	docker pull sonatanfv/sonata-empty-vnf # ubuntu:16.04
	docker tag sonatanfv/sonata-empty-vnf sonata-psa/fw

package:
	son-validate --debug -s -i -t --project projects/sonata-psa
	son-package --project projects/sonata-psa

package-emu: docker-images gen_emu
	son-validate --debug -s -i -t --project projects/sonata-psa-gen-emu
	son-package --project projects/sonata-psa-gen-emu

gen_emu:
	$(MAKE) -C projects gen_emu

.PHONY: gen_emu
