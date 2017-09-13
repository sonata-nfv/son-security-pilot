# PSA's squid FSM

The role of the this FSM is to gather the dynamic configuration bits and finish the squid configuration.


## Creating the PSA service package

Before being configured, the squid service must be running.
To do so, the PSA service must be validated and packaged.

First, at the top level directory, launch the command:
```
make docker-images
```
It will create the Docker image for each VNF of the PSA service.

Then, the PSA service can be packaged with:
```
make package
```
This will validate the service using `son-validate` and build the SONATA package with `son-package`

After this 2 steps, the PSA service package is ready, it should be located at the top level directory:
```
foo@bar:~$ ls son-security-pilot/*.son
son-security-pilot/eu.sonata-nfv.sonata-psa-service.0.5.son
```


## Running the PSA service under `son-emu`

We suppose that a topology is already running.

After the service creation step explained above, the service can be upload in `son-emu` with the command (in the top level directory):
```
son-access --platform emu push --upload eu.sonata-nfv.sonata-psa-service.0.5.son
```

Then, the PSA service is instantiated with the command:
```
son-access --platform emu push --deploy latest
```


## Creating the squid FSM

To create the squid FSM Docker image, first step into the `fsm/squid-config` directory and launch the command:
```
cd fsm/squid-config
make build
```


## Starting the message broker

The SONATA MANO framework relies on a message broker to dispatch events between all components.
A rabbitMQ broker must be running to use and test the FSM.

In the `fsm/squid-config` directory, launch the command:
```
cd fsm/squid-config
make broker
```
It will download a rabbitMQ Docker image and run it in the background.



## Running the squid FSM under `son-emu`

When the PSA service is up and running, the squid FSM can be tested.

In the `fsm/squid-config` directory, use the command:
```
cd fsm/squid-config
make run
```
This will start the squid FSM inside a Docker container alongside a fake FML and SMR.
After starting, the fake FML (`test/fakeFLM.py`) will watch Docker events and the `son-emu` API to find VNFs running as containers.
The fake FML is able to detect VNF already running or their creation, so that the squid FSM can be restarted anytime.
When a VNF is detected, the fake FML will generate and inject a VNFR event inside the broker which will trigger the squid FSM.

### Runnint the squid FSM in development mode under `son-emu`

The following command will start a Docker container to run the squid FSM in development mode:
```
cd fsm/squid-config
make dev
```
It will output a terminal prompt from the container.

Inside this development container, the command:
```
python test/testConf.py
```
Will manually start the squid FSM.

This container mount the squid FMS code in volumes, so you can directly modify, on the host, the files under the following directories:
* `fsm/squid-config/test`
* `fsm/squid-config/sonfsmvprxsquidconfiguration1`
* `fsm/squid-config/ansible`
