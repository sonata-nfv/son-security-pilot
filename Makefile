all: docker-images package

docker-images: docker-image-squid docker-image-snort

docker-image-squid:
	cd install/roles/docker-squid/files && \
	  docker build -t sonata-psa/squid .

docker-image-haproxy:
	cd install/roles/docker-haproxy/files && \
	  docker build -t sonata-psa/haproxy .

docker-image-snort:
	docker pull glanf/snort

package:
	son-validate --debug -s -i -t --project projects/sonata-psa
	son-package --project projects/sonata-psa

