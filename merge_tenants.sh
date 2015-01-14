#!/bin/bash
# Author: kamil.madac@gmail.com
# Merge multiple tenant into one. Reason for this is that there are teams who needs larger quotas and they agree that they share one tenant.
# Tested and used on OpenStack Grizzly install on Ubuntu 12.04 LTS Cloud Archive repo
# Script will create new tenant, sets quotas, networks, security rules, adds users as a tenant members and removes users from their original projects

tenant_name=group.newtenant
users="kamil.madac jozo.muska"

# Create environment
keystone tenant-create --name $tenant_name --description="Lab Environment"
tenantid=$(keystone tenant-list | grep $tenant_name | awk '{print $2}')

# Set quotas to tenant
nova quota-update --floating_ips 20 $tenantid
nova quota-update --ram 20480 $tenantid
nova quota-update --instances 20 $tenantid
nova quota-update --cores 40 $tenantid

# Assign users as a members to tenant
for i in $users; do keystone user-role-add --user $i --role _member_ --tenant $tenantid; done

# Create network infrastructure
externalid=$(quantum net-external-list |  grep external_network | awk '{print $2}')
netid=$(quantum net-create --tenant-id $tenantid ${tenant_name}_private_network | grep "| id" | awk '{print $4}')
subnetid=$(quantum subnet-create --tenant-id $tenantid --name sub_private_network_${tenant_name} $netid 5.1.1.0\/24 | grep "| id" | awk '{print $4}')
routerid=$(quantum router-create --tenant-id $tenantid ${tenant_name}_external_router | grep "| id" | awk '{print $4}')
quantum router-gateway-set $routerid $externalid 
quantum router-interface-add $routerid $subnetid

# Set security groups
# workaround for 414 error (quantum client incorrrectly handles too many quantum security group rules)
# it is necessary to parse debug json output of quantum client
quantum security-group-rule-list -F "tenant_id" -F id -v 2>&1 | grep "DEBUG\: quantumclient\.client RESP" | grep $tenantid |  awk -F'} ' '{print $2}' > /tmp/.json
sec_group_rules=$(python -c "import json; my_data=json.loads(open(\"/tmp/.json\").read()); print(' '.join([i['id'] for i in my_data['security_group_rules'] if i['tenant_id'] == u'$tenantid']))")
for i in $sec_group_rules; do quantum security-group-rule-delete $i; done

sec_group_id=$(quantum security-group-list -c name -c id -c tenant_id | grep default | grep $tenantid | awk '{print $4}')

quantum security-group-rule-create --tenant-id $tenantid --direction ingress --protocol icmp --remote-ip-prefix 0.0.0.0/0 --ethertype IPv4 $sec_group_id
quantum security-group-rule-create --tenant-id $tenantid --direction ingress --protocol tcp --remote-ip-prefix 0.0.0.0/0 --ethertype IPv4 $sec_group_id
quantum security-group-rule-create --tenant-id $tenantid --direction ingress --protocol udp --remote-ip-prefix 0.0.0.0/0 --ethertype IPv4 $sec_group_id

# Remove assignment of users from original tenants
for i in $users; do keystone user-role-remove --user $i --role _member_ --tenant $i; done

