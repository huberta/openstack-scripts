Scripts for debugging openstack deployment
==========================================

## dhcpdump.sh ##

Script is used for debugging connectivity/dhcp issues in quantum/neutron environment. Displays tcpdumps for all involved interfaces in realtime on the screen.
It helps to find which part of quantum path causes problem.

### Using ###

Script has to be run from control node. It suppose thet network node is installed on control node!

    dhcpdump.sh instance_name ip_address_of_internal_network

Example:
    
    dhcpdump.sh quantum_test 192.168.122.5D

### Requirements ###

* tcpdump installed
* multitail installed
* sourced creds file with tenant name, where instance belongs
* nova conf in `/etc/nova/nova.conf` (file is used to get login/pass credentials to nova database)
* passwordless ssh connectivity to compute nodes by root user

### Creds file example ###

    export OS_TENANT_NAME=admin
    export OS_USERNAME=adminlogin
    export OS_PASSWORD=adminpass
    export OS_AUTH_URL="http://192.168.122.200:5000/v2.0/"

### TODO ###

* error/inputs checking
* possbility to execute script in environment where network node is not on the same machine as control node




