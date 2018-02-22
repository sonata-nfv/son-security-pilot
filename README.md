# son-security

This repository contains descriptors, code and images of the SONATA security pilot.

SONATA vCDN pilots depends on the following VNFs and FSM

* Virtual Firewall pfsense
* Virtual Snort
* Virtual Cache
* Virtual TOR
* Virtual VPN

## Packaging the network service project (using `son-cli`)
* `cd projects/`
* `son-package --project sonata-psa`

## Upload the package to the platform (using `son-cli`)
* `son-access auth`
* `son-access --platform int3 --debug push --upload eu.sonata-nfv.sonata-psa.0.5.son`
