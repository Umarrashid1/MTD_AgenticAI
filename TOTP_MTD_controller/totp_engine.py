import time
import hashlib
import hmac

class TOTPMTDEngine:
    def __init__(self, secret_key=b"secret_key_tesi", time_step_ms=30000): 
        # Pre-shared secret and mutation interval 
        self.secret_key = secret_key
        self.time_step_ms = time_step_ms

    def _get_port(self, window_offset=0):
        # Calculate the time slot 
        current_time_ms = int(time.time() * 1000)
        time_slot = (current_time_ms // self.time_step_ms) + window_offset
        message = str(time_slot).encode('utf-8')

        # Python 2.7 Fallback: Use HMAC-SHA256 instead of BLAKE2b
        # We truncate to 2 bytes (16-bit) as required for network ports 
        h = hmac.new(self.secret_key, message, hashlib.sha256)
        digest = h.digest()
        
        # Take the last 2 bytes and convert to integer
        port = (ord(digest[-2]) << 8) | ord(digest[-1])
        
        # Ensure it is not a well-known port 
        return port if port > 1024 else port + 1024

    def get_active_window(self):
        # Returns [prev, current, next] slots to handle jitter 
        return {
            "prev": self._get_port(-1),
            "current": self._get_port(0),
            "next": self._get_port(1)
        }