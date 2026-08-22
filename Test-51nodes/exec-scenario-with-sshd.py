#!/usr/bin/env python


from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.topo import Topo
from mininet.link import TCLink
from functools import partial
from mininet.util import waitListening
from mininet.node import Node

from mininet.util import irange
from mininet.log import info

import time

# Global values
hostIpAddrList = [ [] for i in range(100) ] # [hostId] = [eth0-ip, eth1-ip,...]
hostNeighborList = [ [] for i in range(100) ] # [hostId] = [nbr-ip0, nbr-ip1,...]
num_allHosts = 0
swIndex = 0

# SSH Evn. Setting
enable_ssh = 1 # when 1, ssh to each host can be used.

def setIpAddr( net, hostNum ):
    # Set the ip addr of each host
    for hostId in range(len(hostIpAddrList)):
        nodeName = "h" + str(hostId)
        for index, ipaddr in enumerate(hostIpAddrList[hostId]):
            print(nodeName, "-eth", index, ipaddr)
            command = "ifconfig " + nodeName + "-eth" + str(index) + " " + ipaddr  + " netmask 255.255.255.0"
            print("command:", command)
            net.hosts[hostId].cmd(command)

    # Set ip addr in control plane (sshd segment)
    global enable_ssh
    if enable_ssh == 1:
        global num_allHosts
        for hostId in range(num_allHosts):
            nodeName = "h" + str(hostId)
            ethId = len(hostIpAddrList[hostId])
            ipaddr = "10.0.0." + str(hostId+1)
            command = "ifconfig " + nodeName + "-eth" + str(ethId) + " " + ipaddr
            print(nodeName, command)
            net.hosts[hostId].cmd(command)

def execCommand_For_SetFib( net, hostId, neigh_ipaddr, f_log ):
    nodeName = "h" + str(hostId)
    command = "cefroute add ccnx:/test udp " + neigh_ipaddr + " -d ./" + nodeName 
    print(nodeName, "command:", command)
    info( net.hosts[hostId].cmd(command) )

    # Translate neigh_ipaddr to hostId and Write Log
    for k in range(len(hostIpAddrList)):
        if neigh_ipaddr in hostIpAddrList[k]:
            neigh_hostId = k
            f_log_dat = nodeName + ": " + command + " To:h" + str(neigh_hostId) + "\n"
            f_log.write(f_log_dat)

def setFib( net, hostNum):
    f_fiblist = open("hostFibList_executed.dat", 'w')

    #with open("fib.conf", "r", encoding="utf-8") as f:
    f = open("fib.conf", "r")
    lines = f.readlines()
    for line in lines:
        f_fiblist.write("\n")
        items = line.split()
        if items[0] == "#":
            continue
        hostId = int(items[0])
        hostName = "h" + str(hostId)
        num_neighbors = len(items) - 1
        for i in range(1,(num_neighbors+1)):
            hostId_setToFib = int(items[i])
            #print(hostName, "add neighbor:", hostId_setToFib)
            for neighIp in hostNeighborList[hostId]:
                # Check neighbor-ip(defined in link.conf) is included in the ipaddrlists of host with hostId_setToFib?
                if neighIp in hostIpAddrList[hostId_setToFib]: 
                    execCommand_For_SetFib( net, hostId, neighIp, f_fiblist) 
    f.close()
    
    f_fiblist.close()

def connectToRootNS( network, switch, ip, routes ):
    """Connect hosts to root namespace via switch. Starts network.
      network: Mininet() network object
      switch: switch to connect to root namespace
      ip: IP address for root namespace node
      routes: host networks to route to"""
    # Create a node in root namespace and link to switch 0
    root = Node( 'root', inNamespace=False )
    intf = network.addLink( root, switch ).intf1
    root.setIP( ip, intf=intf )
    # Start network that now includes link to root namespace
    network.start()
    # Add routes from root ns to hosts
    for route in routes:
        root.cmd( 'route add -net ' + route + ' dev ' + str( intf ) )

def sshd( network, cmd='/usr/sbin/sshd', opts='-D',
          ip='10.123.123.1/32', routes=None, switch=None ):
#def sshd( network, cmd='/usr/sbin/sshd', opts='-D',
#          ip='192.168.0.254/32', routes=None, switch=None ):
    """Start a network, connect it to root ns, and run sshd on all hosts.
       ip: root-eth0 IP address in root namespace (10.123.123.1/32)
       routes: Mininet host networks to route to (10.0/24)
       switch: Mininet switch to connect to root namespace (s1)"""
    if not switch:
        print("if not switch")
        switch_name = "s" + str(swIndex)
        print("ssh switch:", switch_name)
        switch = network[ switch_name ]  # switch to use
    if not routes:
        print("if not routes")
        #routes = [ '192.168.0.0/24' ]
        routes = [ '10.0.0.0/16' ]
    connectToRootNS( network, switch, ip, routes )

    command = cmd + ' ' + opts + '&'
    print("command:", command)
    for host in network.hosts:
        host.cmd( cmd + ' ' + opts + '&' )
    info( "*** Waiting for ssh daemons to start\n" )
    for server in network.hosts:
        waitListening( server=server, port=22, timeout=5 )

    #info( "\n*** Hosts are running sshd at the following addresses:\n" )
    #for host in network.hosts:
    #    info( "sshdInfo:", host.name, host.IP(), '\n' )


def runSimpleLink():
    "Create and run simple link network"
    hostNum = 51 
    topo = simpleLinkTopo( n=hostNum )
    link = partial ( TCLink )  # reflect link parameters
    net = Mininet( topo=topo, link=link, waitConnected=True )
    #net.start()

    #print("net.hosts[0]", net.hosts[0]) # --> h0
    #h0 = net.get('h0')

    # Set ip addr of each host
    setIpAddr( net, hostNum)

    # Set sshd env.
    global enable_ssh
    if enable_ssh == 1:
        sshd( net, opts='-D -o UseDNS=no -u0' )
    else:
        net.start()

    # Check ifconfig-result at h0, h1 and h2
    for id in irange( 0, (hostNum-1) ):
      #result = net.hosts[id].cmd("ifconfig")
      #info("hosts[", id, "]-ifconfig:", "\n", result)
      nodeName = "h" + str(id)
      print(nodeName, "command:", "ifconfig")
      #info( net.hosts[id].cmd("ifconfig") )

    # Launch cefnetd 
    for id in irange( 0, 50 ): 
      nodeName = "h" + str(id)
      command = "cefnetdstart -d ./" + nodeName + " > ./Log-cefnetd/" + nodeName + "-cefnetd-log"
      print(nodeName, "command:", command)
      info( net.hosts[id].cmd(command) )
      time.sleep(1)

    # Create Fib 
    setFib( net, hostNum )
    
    # Exec cefputfile at h0
    time.sleep(1)
    nodeId = 0 
    nodeName = "h" + str(nodeId)
    command = "cefputfile ccnx:/test -f ./sample-putfile -t 30000 -e 30000 -d ./" + nodeName  + " > ./Log-cefputfile/" + nodeName + "-cefputfile-log"
    print(nodeName, "command:", command)
    net.hosts[nodeId].cmd(command)

    for contentId in irange( 1, 100 ):
        contentName = "ccnx:/test/" + str(contentId)
        command = "cefputfile " + contentName + " -f ./sample-putfile -t 30000 -e 30000 -d ./" + nodeName  + " > ./Log-cefputfile/" + nodeName + "-cefputfile-log-" + str(contentId)
        print(nodeName, "command:", command)
        time.sleep(0.5)
        net.hosts[nodeId].cmd(command)

    time.sleep(5) # <-- *** Very Important!! one sec is not enough...
   
    # Exec cefgetfile at arbitrary nodes 
    #for nodeId in irange( 0, (hostNum-1) ):
    #    nodeName = "h" + str(nodeId)
    #time.sleep(5)

    CLI( net )
    
    # Exec cefstatus at arbitrary nodes 
    for nodeId in irange( 0, (hostNum-1) ):
        nodeName = "h" + str(nodeId)
        #execNodes = ["h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8", "h9", "h10", "h11", "h12", "h13"]
        execNodes = ["h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8", "h9", "h10", "h11", "h12", "h13", "h14", "h15", "h16", "h17", "h18", "h19", "h19", "h20", "h21", "h22", "h23", "h24", "h25", "h26", "h27", "h28", "h29", "h30", "h31", "h32", "h33", "h34", "h35", "h36", "h37", "h38", "h39", "h40", "h41", "h42", "h43", "h44", "h45", "h46", "h47", "h48", "h49", "h50" ]
        if nodeName in execNodes:
            # Execute cefget as a background-job
            command = "cefstatus -d ./" + nodeName  + " > ./Log-cefstatus/" + nodeName + "-cefstatus-log &"
            print(nodeName, "command:", command)
            net.hosts[nodeId].cmd(command)
            time.sleep(0.5) 
            #time.sleep(1) 


    #CLI( net )
    
    # Stop cefnetd at h0 and h1
    for id in irange( 0, (hostNum-1) ):
     command = "cefnetdstop -d ./h" + str(id)
     info("hosts[", id, "]:", command, "\n")
     net.hosts[id].cmd(command)

    # Stop sshd
    global num_allHosts
    print("num_allHosts:", num_allHosts)
    cmd_sshd = 'kill %/usr/sbin/sshd'
    for host in net.hosts:
        host.cmd( cmd_sshd )
        print(host, cmd_sshd)

    net.stop()

class simpleLinkTopo( Topo ):
    global num_allHosts

    # pylint: disable=arguments-differ
    def build( self, n, **_kwargs ):
        
        # Create host objects
        hosts = [ self.addHost( 'h%s' % h ) for h in irange( 0, (n-1) ) ]       

        # Set links and Create hostIpAddrList and hostNeighborList
        global swIndex 
        #swObj = [ [] for i in range(150)] # [swIndex]=swObj
        swObj = [] # [swIndex]=swObj

        netPrefix = "192.168."
        netPrefixIndex = 1 # 192.168."netPrefixIndex".xx

        with open('./link.conf') as f:

            for line in f:
                print("leadline: ", line.rstrip("\n"))
                if "#" in line:
                    print("Skip!!")
                    continue
                items = line.split()
                node1_id, node2_id = int(items[0]), int(items[1])
                node1_str = "h" + items[0]
                node2_str = "h" + items[1]
                # register the number of all hosts
                global num_allHosts
                if num_allHosts < (node1_id + 1):
                    num_allHosts = node1_id + 1
                if num_allHosts < (node2_id + 1):
                    num_allHosts = node2_id + 1

                print("***Set link:")
                print("create link between", node1_str, node2_str)
                bwValue = 50
                delayValue='1ms'
                lossValue = 0
                for index, item in enumerate(items):
                    if index == 2 and len(items) >= 3:
                        bwValue = int(item)
                        print("bwValue =", bwValue)
                    if index == 3 and len(items) >= 4:
                        delayValue = item
                        print("delayValue =", delayValue)
                    if index == 4 and len(items) >= 5:
                        lossValue = int(item)
                        print("lossValue =", lossValue)

                # Set link
                switch_name = "s" + str(swIndex)
                command = "swObj[" + str(swIndex) + "] = self.addSwitch( '" + switch_name  + "' )"
                print("command:", command)
                swObj.append(self.addSwitch(switch_name))
                #swObj[swIndex] = self.addSwitch(switch_name)
                command = "self.addLink( " + switch_name + ", hosts[" + str(node1_id) + "], bw=" +\
                        str(bwValue) + ", delay='" + delayValue + "', loss=" + str(lossValue) + " )"
                print("command:", command)
                self.addLink( switch_name, hosts[node1_id], bw=bwValue, delay=delayValue, loss=lossValue)
                self.addLink( switch_name, hosts[node2_id])

                swIndex += 1
                # set them to defalut value
                bwValue = 50
                delayValue='1ms'
                lossValue = 0

                # Set hostIpAddr
                node1_ipAddr = netPrefix + str(netPrefixIndex) + ".1"
                hostIpAddrList[node1_id].append(node1_ipAddr)
                node2_ipAddr = netPrefix + str(netPrefixIndex) + ".2"
                hostIpAddrList[node2_id].append(node2_ipAddr)
                netPrefixIndex += 1
                if netPrefixIndex == 255:
                    print("Need change netmask!!!")

                # Set hostNeighborList
                hostNeighborList[node1_id].append(node2_ipAddr)
                hostNeighborList[node2_id].append(node1_ipAddr)

        ### Print hostIpAddrList and hostNeighborList
        f_iplist = open("hostIpAddrList_executed.dat", 'w')
        print("hostIpAddrList")
        for i in range(len(hostIpAddrList)):
            if len(hostIpAddrList[i]):
                print("host", i, ":", hostIpAddrList[i])
                f_iplist_dat = "host" + str(i) + ":" + str(hostIpAddrList[i]) + "\n"
                f_iplist.write(f_iplist_dat)
        print("\n", end="")
        f_iplist.close()

        f_neighlist = open("hostNeighborList_executed.dat", 'w')
        print("hostNeighborList, host-ID expression")
        for i in range(len(hostNeighborList)):
            if len(hostNeighborList[i]):
                print("Neighbors connected to host", i, ":", hostNeighborList[i])
                f_neighlist_dat = "Neighbors connected to host" + str(i) + ":" + str(hostNeighborList[i]) + "\n"
                f_neighlist.write(f_neighlist_dat)
                for j in range(len(hostNeighborList[i])):
                #print("host",i,"neighbor:",hostNeighborList[i][j])
                    for k in range(len(hostIpAddrList)):
                        if len(hostIpAddrList[k]):
                        #print("host", k, "ip:", hostIpAddrList[k])
                            if hostNeighborList[i][j] in hostIpAddrList[k]:
                                print("NeighborHostId:", k, "ip-addr:", hostNeighborList[i][j])
                                f_neighlist_dat = "NeighborHostId: " + str(k) + " ip-addr: " + str(hostNeighborList[i][j]) + "\n"
                                f_neighlist.write(f_neighlist_dat)
        f_neighlist.close()

   
        # Set Control Plane (SSH segment)
        global enable_ssh
        if enable_ssh == 1:
            switch_name = "s" + str(swIndex)
            swObj.append(self.addSwitch(switch_name))
            for hostId in irange( 0, (num_allHosts-1) ):
                self.addLink(switch_name, hosts[hostId])


if __name__ == '__main__':
    setLogLevel( 'info' )
    runSimpleLink()
