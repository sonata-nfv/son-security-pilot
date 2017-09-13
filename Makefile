
docker-images: docker-image-squid

docker-image-squid:
	cd install/roles/docker-squid/files && \
	  docker build -t sonata-psa/squid .

docker-image-haproxy:
	cd install/roles/docker-haproxy/files && \
	  docker build -t sonata-psa/haproxy .

package:
	son-validate --debug --project ns
	son-package --project ns

