#!/usr/bin/python
from mininet.net import Containernet
from mininet.node import RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, setLogLevel

setLogLevel('info')

def create_topology():
    net = Containernet()
    info('*** Adding Remote Ryu Controller\n')
    # Ryu must be running on port 6653 before starting this script
    c0 = net.addController('c0', controller=RemoteController, ip='127.0.0.1', port=6653)

    info('*** Adding Docker containers (External Zone)\n')
    # Attackers
    a1 = net.addDocker('a1', ip='10.0.0.11/24', mac='00:00:00:00:00:11', dimage="kalilinux/kali-rolling")

    info('*** Adding Docker containers (Internal Zone)\n')
    # Legitimate Client
    c1 = net.addDocker('c1', ip='10.0.0.100/24', mac='00:00:00:00:00:AA', dimage="ubuntu:trusty")
    # Decoy?
    decoy = net.addDocker('decoy', ip='10.0.0.200/24', mac='00:00:00:00:00:DD', dimage="vulnerables/web-dvwa")
    # Vulnerable Target
    target = net.addDocker('target', ip='10.0.0.251/24', mac='00:00:00:00:00:FF', dimage="vulnerables/web-dvwa")

    info('*** Adding switches (Core & Edge)\n')
    s1 = net.addSwitch('s1') # Core Switch
    s2 = net.addSwitch('s2') # External Edge
    s3 = net.addSwitch('s3') # Internal Edge

    info('*** Creating links\n')
    # Connect Edges to Core
    net.addLink(s2, s1, cls=TCLink, bw=1000)
    net.addLink(s3, s1, cls=TCLink, bw=1000)

    # Connect External Nodes to s2
    net.addLink(a1, s2, cls=TCLink, delay='5ms')

    # Connect Internal Nodes to s3
    net.addLink(c1, s3, cls=TCLink, delay='2ms')
    net.addLink(decoy, s3, cls=TCLink, delay='2ms')
    net.addLink(target, s3, cls=TCLink, delay='2ms')

    info('*** Starting network\n')
    net.start()

    # Start apache automatically on the web servers so they are ready to be attacked/scanned
    info('*** Starting web services on Target and Decoy\n')
    target.cmd('service apache2 start &')
    decoy.cmd('service apache2 start &')

    info('*** Running CLI\n')
    info('*** NOTE: Pings will fail until your Ryu controller installs routing flows! ***\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()

if __name__ == '__main__':
    create_topology()