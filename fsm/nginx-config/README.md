# NGINX Configuration FSM
FSM to configure the NGINX function that connects to Service Specific Registry (SMR) and performs a self-registration using the SSM/FSM template. Once the registration is done, it subscribes to configuration topic (son.configuration) to receive the VNFR which is sent by the SLM. Finally, it retrieves the VNF's IP address from the VNFR so that it can connect to the VNF and configure/reconfigure it.

## Requires
* Docker
* Python3.4
* RabbitMQ

## Implementation
* Implemented in Python 3.4
* Dependencies: amqp-storm
* The main implementation can be found in: `son-fsm-examples/configuration/configuration.py`

## How to run it
* To run the FSM locally, you need:
 * a running RabbitMQ broker (see general README.md of [son-mano framework repository](https://github.com/sonata-nfv/son-mano-framework) for info on how to do this)
 * a running Service Specific Registry (SMR) connected to the broker (see general README.md of [SMR repository](https://github.com/sonata-nfv/son-mano-framework) for info on how to do this)

* Run the configuration FSM (in a Docker container):
 * (do in `son-security-pilot/`)
 * `docker build -t son-fsm-psaservice1-nginxconfig1 -f fsm/nginx-config/Dockerfile .`
 * `docker run -it --rm --link broker:broker --net sonata --name son-fsm-psaservice1-nginxconfig1  son-fsm-psaservice1-nginxconfig1`

* Or: Run the configuration FSM (directly in your terminal not in a Docker container):
 * Clone `son-sm` reposinginxy
    * (In `son-sm/son-mano-framework/son-mano-base/`)
        * `python setup.py install`
    * (In `son-sm/son-sm-template/`)
        * `python setup.py install`
 * (In `son-security-pilot/fsm/nginx-config/`)
    * `python setup.py`

## How to test it
* Do the following; each in a separate terminal.
    1. Run the SMR container
    2. Run the configuration container
    3. In `son-security-pilot/fsm/nginx-config/test` run `python testConf.py`
