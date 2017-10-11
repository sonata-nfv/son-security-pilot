# Running the PSA FMSs under the SONATA emulator

## Requirement

* The `son-cli` tools suite
* 2 terminals
* `sudo` rights


## Creating the PSA service package

First the PSA service must be validated and packaged using the `son-cli` tools.

At the top level directory, launch the command:
```
make package-emu
```

It will create the Docker image for each VNF of the PSA service and generate a service package for the emulator:
```
(venv) foo@bar:~/son-security-pilot$ ls -l
total 64
-rw-rw-r-- 1 foo foo  5654 oct.  11 15:46 eu.sonata-nfv.sonata-psa-gen-emu.0.8.son
drwxrwxr-x 7 foo foo  4096 oct.  10 15:56 fsm
drwxrwxr-x 2 foo foo 12288 oct.  10 15:52 graphs
drwxrwxr-x 8 foo foo  4096 sept. 13 16:59 install
-rw-rw-r-- 1 foo foo 11357 sept.  4 10:37 LICENSE
-rw-rw-r-- 1 foo foo  1039 oct.   9 17:15 Makefile
drwxrwxr-x 5 foo foo  4096 oct.  10 15:52 projects
-rw-rw-r-- 1 foo foo   523 sept. 25 18:24 README.md
drwxrwxr-x 8 foo foo  4096 sept. 25 16:27 son-sm
drwxrwxr-x 3 foo foo  4096 sept. 25 18:24 ssm
```


## Running the PSA service under `son-emu`

### Start the topology

To run a service, a infrastructure needs to be emulated using `son-emu`.
For this, launch the following command from the top level directory and leave it running:
```
sudo python fsm/emulator/psa_topology.py
```

### Push and deploy the PSA service

The PSA service can now be uploaded in `son-emu`.
At the top level director, use the command (adapt the file name for newer service package):
```
son-access --platform emu push --upload eu.sonata-nfv.sonata-psa-gen-emu.0.8.son
```

Then, the PSA service is instantiated with the command:
```
son-access --platform emu push --deploy latest
```


## Creating the PSA service FSMs

In the `fsm/emulator` directory, use following command to create a docker image containing all the FSMs used in the PSA service:
```
cd fsm/emulator
make build
```


## Starting the PSA message broker

+The SONATA MANO framework relies on a message broker to dispatch events between all components.
A rabbitMQ broker must be running to use and test the FSM.

In the `fsm/squid-config` directory, launch the command:
```
cd fsm/emulator
make broker
```
It will download a rabbitMQ Docker image and run it in the background.


## Runnings the FSMs in development mode


The following command will launch a Docker container with a command prompt:
```
cd fsm/emulator
make dev
```

In it, the command:
```
cd /emulator && python test/test_configuration.py
```
will start the FSMs workflow.
