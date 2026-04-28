# SDN Moving Target Defense (MTD) Project

This repository contains an implementation of a dynamic defense mechanism (**Moving Target Defense**) based on **Software Defined Networking (SDN)**. The system protects critical services by coordinating the mutation of IP addresses and TCP ports (TOTP-based) in a way that is transparent to legitimate users but deceptive to attackers.

## 🚀 Prerequisites

* **Ubuntu** (Tested on 22.04/24.04)
* **Docker** installed and running
* **Containernet** framework installed
* **Ryu SDN Framework** (Accessed via Docker)

---

## 🛠️ Topology Setup

Before starting any controller, you must initialize the network environment.

1. **Cleanup the Network:** Ensure no previous Mininet processes or hanging links are active:
   ```bash
   sudo mn -c
   ```

2. **Launch the Topology:** In a dedicated terminal, start the network script:
   ```bash
   sudo python3 topology.py
   ```
   > **Note:** This script automatically initializes the following containers: `a1` (Attacker), `c1` (Legitimate Client), `target` (Victim Server), and `decoy`.

---

## 🧠 Controller Execution (Ryu)

You can choose between two defense modes. Execute the corresponding command in a new terminal window.

### Option A: IP Shuffle Mode (Main Controller)
This mode implements IP address rotation to hide the true location of the target server.

```bashtwork host \
  -v "$(pwd):/app" \
  -w /app \
  -e PYTHONPATH=. \
  osrg/ryu \
  ryu-manager main_controller.py
```
docker run -it --rm \
  --network host \
  -v "$(pwd):/app" \
  -w /app \
  -e PYTHONPATH=. \
  osrg/ryu \
  ryu-manager main_controller.py
```

### Option B: TOTP Port Mutation Mode (Advanced)
This mode implements time-based TCP port mutation (TOTP). It ensures that only nodes synchronized with the cryptographic secret can access the service. It runs alongside a Layer 2 switching module to handle basic network traffic (ARP/ICMP).

```bash
docker run -it --rm \
  --network host \
  -v "$(pwd):/app" \
  -w /app \
  -e PYTHONPATH=. \
  osrg/ryu \
  ryu-manager ryu.app.simple_switch_13 totp_controller.py
```

---

## 🧪 Experiment Validation

Once the controller is active and has pushed the flow rules to the switches, perform the following tests within the Containernet CLI.

### 1. Initialize the Web Server
Start the HTTP service on the target node:
```bash
containernet> target python3 -m http.server 80 &
```

### 2. Authorized Client Test (c1)
The user `c1` is authorized by the controller. It should successfully receive the HTML response:
```bash
containernet> c1 curl --connect-timeout 5 [http://10.0.0.3:80](http://10.0.0.3:80)
```
**Expected Result:** Success (HTML Directory Listing received).

### 3. Attacker Test (a1)
The attacker `a1` does not possess the TOTP secret and is blocked by the edge switch firewall:
```bash
containernet> a1 curl --connect-timeout 5 [http://10.0.0.3:80](http://10.0.0.3:80)
```
**Expected Result:** `curl: (28) Connection timed out` (The packet is silently dropped by the switch).

---

## 📂 File Structure

* **`network`**: Network definition (3 switches, 4 Docker hosts).
* **`test controller`**: our own SDN implementation.
* **`totp_mtd_controller`**: totp MTD implementation.

---
