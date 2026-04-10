# config.py

# Rete e Host
REAL_HOSTS = ['10.0.0.1', '10.0.0.2', '10.0.0.3']
VIRTUAL_IP_SUBNET = "10.0.0."
VIRTUAL_IP_RANGE = (100, 200)

# Timer di Mutazione (Jitter in secondi)
SHUFFLE_MIN_TIME = 20
SHUFFLE_MAX_TIME = 45

# Impostazioni Switch
HARD_TIMEOUT = 20  # o idle_timeout se preferisci