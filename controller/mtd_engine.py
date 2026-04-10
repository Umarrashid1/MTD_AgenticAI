import random
import config

class MTDEngine(object):
    """
    Moving Target Defense Engine responsible for IP Mutation logic.
    It manages the mapping between Real IPs and Virtual (Mutable) IPs.
    """
    def __init__(self):
        # List of physical/static IP addresses in the network
        self.real_hosts = config.REAL_HOSTS
        # Forward mapping: Real IP -> Virtual IP
        self.real_to_virtual = {}
        # Reverse mapping: Virtual IP -> Real IP
        self.virtual_to_real = {}

    def shuffle_ips(self):
        """
        Generates a new set of unique Virtual IPs for each real host.
        Returns the new mapping dictionary.
        """
        new_real_to_virt = {}
        used_ips = set()

        for real_ip in self.real_hosts:
            while True:
                # Construct a new Virtual IP using the subnet and a random host part
                new_v_ip = config.VIRTUAL_IP_SUBNET + str(random.randint(*config.VIRTUAL_IP_RANGE))
                
                # Ensure the generated Virtual IP is unique within this shuffle cycle
                if new_v_ip not in used_ips:
                    used_ips.add(new_v_ip)
                    new_real_to_virt[real_ip] = new_v_ip
                    break
        
        # Update the internal state with the new mappings
        self.real_to_virtual = new_real_to_virt        
        self.virtual_to_real = {v: k for k, v in self.real_to_virtual.items()}
        
        return self.real_to_virtual

    def get_real_ip(self, virtual_ip):
        """ Returns the Real IP associated with a Virtual IP (Inbound NAT) """
        return self.virtual_to_real.get(virtual_ip)

    def get_virtual_ip(self, real_ip):
        """ Returns the Virtual IP associated with a Real IP (Outbound NAT/Masking) """
        return self.real_to_virtual.get(real_ip)
    
    def is_virtual_ip(self, ip):
        """ Checks if the given IP is currently a registered Virtual IP """
        return ip in self.virtual_to_real
        
    def is_real_ip(self, ip):
        """ Checks if the given IP is a registered Real IP of an internal host """
        return ip in self.real_to_virtual