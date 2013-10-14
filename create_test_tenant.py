__author__ = 'kmadac'

import keystoneclient.v2_0.client as ksclient
import keystoneclient.apiclient.exceptions
import neutronclient.v2_0.client as nclient
import neutronclient.common.exceptions

import argparse

endpoint = "http://192.168.122.200:35357/v2.0"
keystone_url = "http://192.168.122.200:5000/v2.0"
admin_token = "ADMIN"


def create_tenant(keystone, useremail):
    new_tenant = None
    try:
        new_tenant = keystone.tenants.create(tenant_name=useremail, description="Testing tenant", enabled=True)
    except keystoneclient.apiclient.exceptions.Conflict:
        print "Tenant {0} already exists".format(useremail)
        new_tenant = keystone.tenants.find(name=useremail)

    return new_tenant


def create_user(keystone, useremail, password, tenant, role_name='_member_'):
    new_user = None
    try:
        new_user = keystone.users.create(name=useremail, password=password, email=useremail, tenant_id=tenant.id)
    except keystoneclient.apiclient.exceptions.Conflict:
        print "User {0} already exists".format(useremail)
        new_user = keystone.users.find(name=useremail)

    member_role = keystone.roles.find(name=role_name)

    try:
        keystone.roles.add_user_role(new_user, member_role, tenant)
    except keystoneclient.apiclient.exceptions.Conflict:
        print "User {0} already has role {1} in tenant {2}".format(new_user.name, member_role.name, tenant.name)

    admin_user = keystone.users.find(name='admin')
    admin_role = keystone.roles.find(name='admin')
    try:
        keystone.roles.add_user_role(admin_user, admin_role, tenant)
    except keystoneclient.apiclient.exceptions.Conflict:
        print "User {0} already has role {1} in tenant {2}".format(admin_user.name, admin_role.name, tenant.name)

    return new_user


def create_internal_network(neutron, network_name='private_network', network_address='192.168.0.0/24'):
    neutron.format = 'json'

    networks = neutron.list_networks()
    network = None

    # check whether private network exists
    for net in networks['networks']:
        if net['name'] == network_name:
            network = net
            print "Network {0} already exists".format(network_name)
            break

    if not network:
        networkdict = {'name': network_name, 'admin_state_up': True}
        network = neutron.create_network({'network': networkdict})

    subnet = None
    try:
        subnet = neutron.create_subnet({'subnet': {'name': 'sub_'+network_name,
                                        'network_id': network['id'],
                                        'ip_version': 4,
                                        'cidr': network_address}})
    except neutronclient.common.exceptions.NeutronClientException:
        print "Subnet {0} already exists".format(network_address)

    return network, subnet


def main():
    parser = argparse.ArgumentParser(description='Script for creating testing tenant')
    parser.add_argument('user_email', action="store", help="User email will be used as name of tenant")
    parser.add_argument('password', action="store", help="Password for user", default='Start123')

    args = parser.parse_args()

    keystone = ksclient.Client(token=admin_token, endpoint=endpoint)
    new_tenant = create_tenant(keystone, args.user_email)
    create_user(keystone, args.user_email, password=args.password, tenant=new_tenant)

    admin_user = keystone.users.find(name='admin')

    neutron = nclient.Client(username='admin',
                             password='admin_pass',
                             tenant_name=new_tenant.name,
                             auth_url=keystone_url)
    create_internal_network(neutron)



if __name__ == "__main__":
    main()
