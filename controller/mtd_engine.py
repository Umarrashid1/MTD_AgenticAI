# mtd_engine.py
import random
import config

class MTDEngine(object):
    """
    Moving Target Defense Engine.
    Handles the mathematical generation and mapping of Virtual IPs and Virtual Ports.
    Does not interact with Ryu or OpenFlow directly.
    """
    def __init__(self):
        self.real_hosts = config.REAL_HOSTS
        
        # IP Mappings
        self.real_to_virtual_ip = {}
        self.virtual_to_real_ip = {}
        
        # Port Mappings: Format -> {('Real_IP', Real_Port): Virtual_Port}
        self.real_to_virtual_port = {}
        self.virtual_to_real_port = {}

    def shuffle_all(self):
        """ Triggers both IP and Port shuffling algorithms. """
        self._shuffle_ips()
        self._shuffle_ports()
        return self.real_to_virtual_ip, self.real_to_virtual_port

    def _shuffle_ips(self):
        """ Generates unique Virtual IPs for each real host. """
        new_r2v = {}
        used_ips = set()

        for real_ip in self.real_hosts:
            while True:
                new_v_ip = config.VIRTUAL_IP_SUBNET + str(random.randint(*config.VIRTUAL_IP_RANGE))
                if new_v_ip not in used_ips:
                    used_ips.add(new_v_ip)
                    new_r2v[real_ip] = new_v_ip
                    break
        
        self.real_to_virtual_ip = new_r2v        
        self.virtual_to_real_ip = {v: k for k, v in self.real_to_virtual_ip.items()}

    def _shuffle_ports(self):
        """ Generates unique Virtual Ports for protected services. """
        new_r2v = {}
        new_v2r = {}
        used_ports = set()

        for real_ip, real_port in config.PROTECTED_SERVICES.items():
            while True:
                virt_port = random.randint(*config.PORT_RANGE)
                if virt_port not in used_ports:
                    used_ports.add(virt_port)
                    # Mapping logic
                    new_r2v[(real_ip, real_port)] = virt_port
                    new_v2r[(real_ip, virt_port)] = real_port
                    break
        
        self.real_to_virtual_port = new_r2v
        self.virtual_to_real_port = new_v2r

    # --- IP GETTERS ---
    def get_real_ip(self, virtual_ip):
        return self.virtual_to_real_ip.get(virtual_ip)

    def get_virtual_ip(self, real_ip):
        return self.real_to_virtual_ip.get(real_ip)
    
    def is_virtual_ip(self, ip):
        return ip in self.virtual_to_real_ip
        
    def is_real_ip(self, ip):
        return ip in self.real_to_virtual_ip

    # --- PORT GETTERS ---
    def get_real_port(self, real_ip, virtual_port):
        """ Returns the real port given the real destination IP and the virtual port. """
        return self.virtual_to_real_port.get((real_ip, virtual_port))

    def get_virtual_port(self, real_ip, real_port):
        """ Returns the virtual masked port given the real source IP and real port. """
        return self.real_to_virtual_port.get((real_ip, real_port))