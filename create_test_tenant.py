__author__ = 'kmadac'

import keystoneclient.v2_0.client as ksclient
import keystoneclient.apiclient.exceptions

import argparse

endpoint = "http://192.168.122.200:35357/v2.0"
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
        new_user = keystone.tenants.find(name=useremail)

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


def main():
    parser = argparse.ArgumentParser(description='Script for creating testing tenant')
    parser.add_argument('user_email', action="store", help="User email will be used as name of tenant")

    args = parser.parse_args()

    keystone = ksclient.Client(token=admin_token, endpoint=endpoint)
    new_tenant = create_tenant(keystone, args.user_email)
    create_user(keystone, args.user_email, password='lol', tenant=new_tenant)

if __name__ == "__main__":
    main()
