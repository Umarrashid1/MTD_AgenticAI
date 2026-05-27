# config.py

# ==========================================
# CRYPTOGRAPHIC SETTINGS
# ==========================================
# Pre-shared secret key used for HMAC-SHA256 generation
SECRET_KEY = b"secret_key_tesi"

# Mutation interval in milliseconds (e.g., 30000 ms = 30 seconds)
TIME_STEP_MS = 30000

# ==========================================
# NETWORK TOPOLOGY CONFIGURATION
# ==========================================
PEER_A_IP = "10.0.0.1"    # Authorized Client (c1)
PEER_B_IP = "10.0.0.3"    # Target Server (Victim / Juice Shop)

# The actual real port the backend service is listening on
SERVICE_PORT = 80