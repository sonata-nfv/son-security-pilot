# Running the PSA FMSs under the SONATA emulator

## Requirement

* The `son-cli` tools suite
* 2 terminals
* `sudo` rights
* `openvpn` client CLI 


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


## Injecting the host traffic in the PSA service

### Creating a separate routing table 

Starting the vpn client will redirect all the host traffic into the PSA service.
But as this service is also running on the same host (in Docker containers), their outgoing traffics will also be intercepted.
To avoid this loop, the traffic leaving the PSA service through the `cpoutput` interface need to pass by a separate routing table.

First, create an empty routing table called `backup.out` with the command:
```
sudo echo "901   backup.out" >> /etc/iproute2/rt_tables
```

Here, the `10.10.1.0/24` network corresponds to the `cpoutput` interface for the PSA service.
This value value can be found with: `ip addr show sap.cpoutput`.
The following commands will attach the network `10.10.1.0/24` to the `backup.out` table.
The traffic initiated by this network will be handled by the new routing table.
```
sudo ip rule add from 10.10.1.0/24 table backup.out
```

Finally, the next command sets up the routes so that:
* The traffic targeting the `10.10.1.0/24` goes in the `sap.cpoutput` interface with its ip
* The outgoing traffic has a default route to leave the host through the `eth0` interface and the `1.2.3.4` gateway. (The parameters for this rule an by find with the command `route -n` and look at the line corresponding to the `0.0.0.0` destination).
```
sudo ip route add 10.10.1.0/24 dev sap.cpoutput src 10.10.1.1 table backup.out
sudo ip route add default via 1.2.3.4 dev eth0 table backup.out
```

**Note that when the PSA service is stopped, the corresponding interface will be removed. When it happens, the kernel will delete the route corresponding to their network. During development, when you re-start the PSA service, the `sudo ip route add 10.10.1.0/24 dev sap.cpoutput src 10.10.1.1 table backup.out` command needs to be executed again.**

### Extra

You can show the current `backup.out` table's rules with: `ip route show table backup.out`.
To see with table is attached to a network, you can use the `ip rule` command.


## Connecting to the PSA VPN entrypoint

When the vpn FSM configure the VPN, it generates a client configuration file.
This file needs to be retreive to connect to the server automatically.
It contains the server address and the various authentication keys.
This command will copy the `client.ovpn` file from the VPN container to the current local directory:
```
docker cp mn.vnf_vpn:/root/client.ovpn .
```

The PSA service contains a VPN server used as an entrypoint to protect the traffic between the end-user and the VNFs (when the service hosted in a remote platform).
The following command will start a OpenVPN client. It will connect to the PSA service and redirect the host's traffic into the PSA service:
```
sudo openvpn --config client.ovpn
```
