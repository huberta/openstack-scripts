__author__ = 'kmadac'
"""
Script prepares new tenant with the following properties:
1. Create new tenant. Name is specified as a user email as command line parameter
2. Creates new user and this user is added _member_ to tenant. Password is second argument of script
3. Admin user will be added to tenant with role admin
4. Private network is created
5. Router is created
6. Router is connected to external network and to private network
"""

import os
import keystoneclient.v2_0.client as ksclient
import keystoneclient.apiclient.exceptions
import neutronclient.v2_0.client as nclient
import neutronclient.common.exceptions
import novaclient.v1_1.client as novaclient

import argparse

import pdb

def get_keystone_creds():
    d = dict()
    d['username'] = os.environ['OS_USERNAME']
    d['password'] = os.environ['OS_PASSWORD']
    d['auth_url'] = os.environ['OS_AUTH_URL']
    return d

def get_nova_creds():
    d = dict()
    d['username'] = os.environ['OS_USERNAME']
    d['api_key'] = os.environ['OS_PASSWORD']
    d['auth_url'] = os.environ['OS_AUTH_URL']
    return d

def get_service_creds():
    d = dict()
    d['token'] = os.environ['OS_SERVICE_TOKEN']
    d['endpoint'] = os.environ['OS_SERVICE_ENDPOINT']
    return d

def create_tenant(keystone, useremail):
    new_tenant = None
    try:
        new_tenant = keystone.tenants.create(tenant_name=useremail, description="Closed Beta Test", enabled=True)
    except keystoneclient.apiclient.exceptions.Conflict:
        print "Tenant {0} already exists".format(useremail)
        new_tenant = keystone.tenants.find(name=useremail)

    return new_tenant


def create_and_assign_users(keystone, useremail, password, tenant, role_name='_member_', username=None, assign_admin=False):
    new_user = None

    if not username:
        username=useremail

    try:
        new_user = keystone.users.create(name=username, password=password, email=useremail, tenant_id=tenant.id)
    except keystoneclient.apiclient.exceptions.Conflict:
        print "User {0} already exists".format(useremail)
        new_user = keystone.users.find(name=username)

    member_role = keystone.roles.find(name=role_name)

    try:
        keystone.roles.add_user_role(new_user, member_role, tenant)
    except keystoneclient.apiclient.exceptions.Conflict:
        print "User {0} already has role {1} in tenant {2}".format(new_user.name, member_role.name, tenant.name)

    if assign_admin:
        admin_user = keystone.users.find(name='admin')
        admin_role = keystone.roles.find(name='admin')
        try:
            keystone.roles.add_user_role(admin_user, admin_role, tenant)
        except keystoneclient.apiclient.exceptions.Conflict:
            print "User {0} already has role {1} in tenant {2}".format(admin_user.name, admin_role.name, tenant.name)

    return new_user


def unassign_admin_from_tenant(keystone, tenant):
    admin_user = keystone.users.find(name='admin')
    admin_role = keystone.roles.find(name='admin')
    try:
        keystone.roles.remove_user_role(admin_user, admin_role, tenant)
    except NotFound as e:
        print "Unassignment unsuccesfull: {0}".format(e.msg)
        return False
    
    return True

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
        network = neutron.create_network({'network': networkdict})['network']

    subnet = None
    try:
        subnet = neutron.create_subnet({'subnet': {'name': 'sub_'+network_name,
                                        'network_id': network['id'],
                                        'ip_version': 4,
                                        'cidr': network_address}})
    except neutronclient.common.exceptions.NeutronClientException:
        print "Subnet {0} already exists".format(network_address)

    return network, subnet


def preset_default_security_group(neutron, tenant):
    # find default sucurity group id
    security_groups = neutron.list_security_groups()['security_groups']
    def_sec_group_id = [secg['id'] for secg in security_groups if secg['name'] == 'default' and secg['tenant_id'] == tenant.id][0]

    # define request bodies
    sec_group_rule_icmp = {'security_group_rule': { 'direction': 'ingress', 
                                                    'security_group_id': def_sec_group_id, 
                                                    'port_range_min': None, 
                                                    'port_range_max': None, 
                                                    'protocol': 'icmp',  
                                                    'remote_group_id': None, 
                                                    'remote_ip_prefix': '0.0.0.0/0' }}

    sec_group_rule_tcp = {'security_group_rule': { 'direction': 'ingress', 
                                                   'security_group_id': def_sec_group_id, 
                                                   'port_range_min': None, 
                                                   'port_range_max': None, 
                                                   'protocol': 'tcp', 
                                                   'remote_group_id': None, 
                                                   'remote_ip_prefix': '0.0.0.0/0' }}

    sec_group_rule_udp = {'security_group_rule': { 'direction': 'ingress', 
                                                   'security_group_id': def_sec_group_id, 
                                                   'port_range_min': None, 
                                                   'port_range_max': None, 
                                                   'protocol': 'udp',  
                                                   'remote_group_id': None, 
                                                   'remote_ip_prefix': '0.0.0.0/0' }}

    # send requests to create groups
    try:
        neutron.create_security_group_rule(sec_group_rule_icmp)
    except neutronclient.common.exceptions.NeutronClientException as e:
        print "Scurity group exists {0}".format(e.message)

    try:
        neutron.create_security_group_rule(sec_group_rule_tcp)
    except neutronclient.common.exceptions.NeutronClientException as e:
        print "Scurity group exists {0}".format(e.message)

    try:
        neutron.create_security_group_rule(sec_group_rule_udp)
    except neutronclient.common.exceptions.NeutronClientException as e:
        print "Scurity group exists {0}".format(e.message)

    # delete default rules in default group
    security_group_rules = neutron.list_security_group_rules()['security_group_rules']
    def_sec_group_rules_id = [secgr['id'] for secgr in security_group_rules if secgr['tenant_id'] == tenant.id and secgr['protocol'] == None and secgr['direction'] == 'ingress']

    for secrule_id in def_sec_group_rules_id:
        neutron.delete_security_group_rule(secrule_id)

def create_router(neutron, router_name='tenant_to_public', external_net_name='ext_net',
                  private_subnet_name='sub_private_network'):

    router = neutron.list_routers(name=router_name)['routers']

    if not router:
        router = neutron.create_router({'router': {'name': router_name, 'admin_state_up': True}})
        router_id = router['router']['id']
    else:
        print "Router {0} already exists".format(router_name)
        router_id = router[0]['id']

    # connect router to external network

    external_net = neutron.list_networks(name=external_net_name)['networks']

    if external_net:
        neutron.add_gateway_router(router_id, {'network_id': external_net[0]['id']})
    else:
        print "Error: External network {0} not found. Router not connected!".format(external_net_name)

    # connect router to private network

    private_subnet = neutron.list_subnets(name=private_subnet_name)['subnets']
    if private_subnet:
        try:
            neutron.add_interface_router(router_id, {'subnet_id': private_subnet[0]['id']})
        except neutronclient.common.exceptions.NeutronClientException as e:
            print e.message
    else:
        print "Error: Private subnet {0} not found. Router not connected!".format(private_subnet)


def main():
    parser = argparse.ArgumentParser(description='Script for creating testing tenant')
    parser.add_argument('user_email', action="store", help="User email will be used as name of tenant")
    parser.add_argument('password', action="store", help="Password for user")
    parser.add_argument('--extnet', '-e', action="store", default='external_network', help="Name of external network")
    parser.add_argument('--tenusername', '-t', action="store", help="Default tenant and user name is email address, but can be overriden with this parameter")

    args = parser.parse_args()

    if args.tenusername:
        new_tenant_name = args.tenusername
        new_user_name = args.tenusername
    else:
        new_tenant_name = args.user_email
        new_user_name = args.user_email

    service_creds = get_service_creds()
    keystone_creds = get_keystone_creds()

    keystone = ksclient.Client(**service_creds)
    new_tenant = create_tenant(keystone, new_tenant_name)
    create_and_assign_users(keystone, args.user_email, password=args.password, tenant=new_tenant, username=new_user_name, assign_admin=True)

    keystone_creds['tenant_name'] = new_tenant.name
    neutron = nclient.Client(**keystone_creds)

    create_internal_network(neutron, network_name='private_network_'+new_tenant_name, network_address='5.1.1.0/24')
    create_router(neutron, router_name='external_router_'+new_tenant_name, external_net_name=args.extnet, private_subnet_name='sub_private_network_'+new_tenant_name)
    preset_default_security_group(neutron, new_tenant)

    ncreds = get_nova_creds()
    ncreds['project_id'] = new_tenant.name
    nova = novaclient.Client(**ncreds)
    nova.quotas.update(new_tenant.id, 
                       ram=25600, cores=40, injected_file_content_bytes=10240, 
                       instances=20, key_pairs=10, floating_ips=20, security_groups=20, security_group_rules=40)

    unassign_admin_from_tenant(keystone, new_tenant)

if __name__ == "__main__":
    main()
