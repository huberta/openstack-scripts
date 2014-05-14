#!/bin/bash
GREP=/bin/grep
AWK=/usr/bin/awk
CUT=/usr/bin/cut
QUANTUM=/usr/bin/quantum
KEYSTONE=/usr/bin/keystone
NOVA=/usr/bin/nova
MULTITAIL=/usr/bin/multitail
IP=/sbin/ip
TCPDUMP="/usr/sbin/tcpdump -ln -e"
TCPDUMPFILTER="'(port bootps) or icmp'"
LOCALHOSTNAME=`/bin/hostname -f`
GAWK=/usr/bin/gawk

if [ $# -lt 2 ]; then
echo "Usage: $0 <fixed_ip> <tenant_name>";
echo "";
echo "<fixed_ip> - IP address of VM in fixed network";
echo "<tenant_name> - Name of tenant, where VM belongs";
echo "";
exit 1;
fi


INTERNALIP=$1
TENANT_NAME=$2

# find tenant id
TENANT_ID=`$KEYSTONE tenant-list | $GREP $TENANT_NAME | $AWK -F" | " '{print $2}'`

if [[ -z "$TENANT_ID" ]]; then
  echo "Error: Tenant ID not found for $TENANT_NAME!!!"
  exit 1
fi

# get all ports from quantum filtered by fixed IP
PORTS_WITH_IP=`$QUANTUM port-list | grep $INTERNALIP | $AWK -F" | " '{print $2}'`

# find VM name for which has specified fixed IP and belongs to specified tenant
for PORT in $PORTS_WITH_IP;
do
  PORT_INFO=`$QUANTUM port-show $PORT | $AWK '/ device_id / { print $4 } / id / { print $4 } / tenant_id / { print $4 } / network_id / { print $4 }'`
  VM_ID=`echo $PORT_INFO | $CUT -d" " -f 1`
  INT_SUFFIX=`echo $PORT_INFO | $AWK '{print substr($2, 0, 11)}'`
  NET_ID=`echo $PORT_INFO | $CUT -d" " -f 3`
  if [[ $PORT_INFO == *$TENANT_ID* ]]; then
    VM_INFO=`$NOVA show $VM_ID | $AWK '/ OS-EXT-SRV-ATTR:hypervisor_hostname / { print $4 } / name / { print $4 }'`
    HYPERVISORNAME=`echo $VM_INFO | $CUT -d" " -f 1`
    VM_NAME=`echo $VM_INFO | $CUT -d" " -f 2`
    break
  fi
done

if [[ -z "$VM_NAME" ]]; then
  echo "Error: VM with IP $INTERNALIP not found!!!"
  exit 1
fi

if [[ -z "$HYPERVISORNAME" ]]; then
  echo "Error: Hypervisor name not found for $VM_NAME!!!"
  exit 1
fi

if [[ -z "$INT_SUFFIX" ]]; then
  echo "Error: Cannot determine interface suffix for IP $INTERNALIP!!!"
  exit 1
fi

DHCP_TAP=`$IP netns exec qdhcp-$NET_ID $IP a | $GREP inet | $GREP tap | $AWK -F" " '{print $7}'`

if [[ -z "$DHCP_TAP" ]]; then
  echo "Error: Missing tap interface in DHCP namespace: qdhcp-$NET_ID!!!"
  exit 1
fi

echo "VMname = $VM_NAME"
echo "Hypervisor = $HYPERVISORNAME"
echo "Interface suffix = $INT_SUFFIX"
#echo "Subnet = $SUBNET_ID"
echo "Net = $NET_ID"
echo "DHCP Tap = $DHCP_TAP"

if [[ "$LOCALHOSTNAME" != "$HYPERVISORNAME" ]]; then
  SSH="ssh root@$HYPERVISORNAME"
  echo "VM on remote host"
fi

$MULTITAIL -l "ip netns exec qdhcp-$NET_ID $TCPDUMP -i $DHCP_TAP $TCPDUMPFILTER"\
           -l "$SSH $TCPDUMP -i qvo$INT_SUFFIX $TCPDUMPFILTER"\
           -l "$SSH $TCPDUMP -i qvb$INT_SUFFIX $TCPDUMPFILTER"\
           -l "$SSH $TCPDUMP -i qbr$INT_SUFFIX $TCPDUMPFILTER"\
           -r 20 -l "$SSH $TCPDUMP -i tap$INT_SUFFIX $TCPDUMPFILTER"

