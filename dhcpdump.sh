#!/bin/bash
GREP=/bin/grep
AWK=/usr/bin/awk
QUANTUM=/usr/bin/quantum
MULTITAIL=/usr/bin/multitail
IP=/sbin/ip
MYSQL=/usr/bin/mysql
TCPDUMP="/usr/sbin/tcpdump -ln -e"
TCPDUMPFILTER="'(port bootps) or icmp'"
LOCALHOSTNAME=`/bin/hostname`
GAWK=/usr/bin/gawk

VMNAME=$1
INTERNALIP=$2

NOVADBUSER=`$GAWK 'match($0,/mysql:\/\/(.*):(.*)@(.*)\//, a) {print a[1]}' /etc/nova/nova.conf`
NOVADBPASS=`$GAWK 'match($0, /mysql:\/\/(.*):(.*)@(.*)\//, a) {print a[2]}' /etc/nova/nova.conf`
DBHOST=`$GAWK 'match($0, /mysql:\/\/(.*):(.*)@(.*)\//, a) {print a[3]}' /etc/nova/nova.conf`

HYPERVISORNAME=`$MYSQL -h $DBHOST -u$NOVADBUSER -p$NOVADBPASS -B -D nova -e "select host from instances where display_name='$VMNAME';" | grep -v host`
INT_SUFFIX=`$QUANTUM port-list |  $GREP $INTERNALIP | $AWK -F" | " '{print substr($2, 0, 11)}'`
SUBNET_ID=`$QUANTUM port-list |  $GREP $INTERNALIP | $AWK -F": " '{print substr($2, 2, 36)}'`
NET_ID=`$QUANTUM net-list | $GREP $SUBNET_ID | $AWK -F" | " '{print substr($2,1,36)}'`
DHCP_TAP=`$IP netns exec qdhcp-$NET_ID $IP a | $GREP inet | $GREP tap | $AWK -F" " '{print $7}'`

echo "VMname = $VMNAME"
echo "Hypervisor = $HYPERVISORNAME"
echo "Interface suffix = $INT_SUFFIX"
echo "Subnet = $SUBNET_ID"
echo "Net = $NET_ID"
echo "DHCP Tap = $DHCP_TAP"

if [ $LOCALHOSTNAME != $HYPERVISORNAME ]; then
  SSH="ssh root@HYPERVISORNAME"
  echo "VM on remote host"
fi

$MULTITAIL -l "ip netns exec qdhcp-$NET_ID $TCPDUMP -i $DHCP_TAP $TCPDUMPFILTER"\
           -l "$SSH $TCPDUMP -i qvo$INT_SUFFIX $TCPDUMPFILTER"\
           -l "$SSH $TCPDUMP -i qvb$INT_SUFFIX $TCPDUMPFILTER"\
           -l "$SSH $TCPDUMP -i qbr$INT_SUFFIX $TCPDUMPFILTER"\
           -r 20 -l "$SSH $TCPDUMP -i tap$INT_SUFFIX $TCPDUMPFILTER"

