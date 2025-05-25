#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.topo import Topo

class SimpleEnterpriseTopo(Topo):
    """
    Topología simple simulando dos 'departamentos' conectados.
    h1, h2 <--> s1 <--> s2 <--> h3, h4
    """
    def build(self):
        # Añadir switches
        info("Añadiendo switches...\n")
        switch1 = self.addSwitch('s1')
        switch2 = self.addSwitch('s2')

        # Añadir hosts
        info("Añadiendo hosts...\n")
        host1 = self.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
        host2 = self.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
        host3 = self.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')
        host4 = self.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:00:04')

        # Añadir enlaces
        info("Añadiendo enlaces...\n")
        # Hosts al Switch 1
        self.addLink(host1, switch1)
        self.addLink(host2, switch1)

        # Hosts al Switch 2
        self.addLink(host3, switch2)
        self.addLink(host4, switch2)

        # Switches entre sí
        self.addLink(switch1, switch2)

def run_network():
    """
    Crea y ejecuta la red Mininet.
    """
    # Usar el controlador remoto os-ken (asume que está en localhost:6653)
    c0 = RemoteController('c0', ip='127.0.0.1', port=6653)

    # Crear la topología
    topo = SimpleEnterpriseTopo()

    # Crear la red
    net = Mininet(
        topo=topo,
        switch=OVSSwitch,
        controller=c0,
        autoSetMacs=True, # Puede ser útil, aunque definimos MACs arriba
        autoStaticArp=True # Simplifica ARP
    )

    info("Iniciando la red...\n")
    net.start()

    info("Red iniciada. Abriendo CLI...\n")
    CLI(net) # Abre la interfaz de línea de comandos de Mininet

    info("Deteniendo la red...\n")
    net.stop()

if __name__ == '__main__':
    # Define el nivel de logging para ver qué está pasando
    setLogLevel('info')
    run_network()
