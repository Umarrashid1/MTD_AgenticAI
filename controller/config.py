# config.py

# ==========================================
# NETWORK CONFIGURATION
# ==========================================
# List of real, physical IP addresses in the network
REAL_HOSTS = [
    "10.0.0.100", # c1
    "10.0.0.200", # decoy
    "10.0.0.251"  # target
]

# Subnet used to generate fake Virtual IPs
VIRTUAL_IP_SUBNET = "10.0.0."
VIRTUAL_IP_RANGE = (100, 200)

# Virtual MAC prefix (00:00:00: followed by casual numbers)
VIRTUAL_MAC_PREFIX = "00:00:00"

# ==========================================
# PORT SHUFFLING CONFIGURATION
# ==========================================
# Range for generating fake Virtual Ports
PORT_RANGE = (50000, 60000)

# Dictionary defining which real host has which real service port
# Example: Host 10.0.0.2 runs a Web Server on port 80
PROTECTED_SERVICES = {
    '10.0.0.2': 80
}

# ==========================================
# TIMING & HARDWARE CONFIGURATION
# ==========================================
# Jitter interval for MTD Shuffling (in seconds)
SHUFFLE_MIN_TIME = 20
SHUFFLE_MAX_TIME = 45

# Idle timeout for Hardware Offloading in the Switch TCAM
HARDWARE_IDLE_TIMEOUT = 10