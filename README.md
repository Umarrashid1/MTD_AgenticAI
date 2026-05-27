# SDN Moving Target Defense (TOTP-MTD) Project

This repository contains a proactive **Moving Target Defense (MTD)** framework based on **Software Defined Networking (SDN)**. The system protects critical network services by continuously mutating transport-layer parameters (TCP ports) using a synchronized Time-Based One-Time Password (TOTP) algorithm via HMAC-SHA256. This mutation remains transparent to authorized endpoints while creating a "Stealth Firewall" that silently drops unauthorized scanning and exploitation attempts.

## 🚀 Prerequisites

* **Ubuntu** (Tested on 22.04/24.04)
* **Docker** installed and running
* **Containernet** framework installed
* **Ryu SDN Framework** (Accessed via Docker)

---

## 📂 Project Structure

* **`network/`**: Contains the Containernet topology script (`topology.py`) to emulate the network environment (3 switches, 4 Docker hosts).
* **`TOTP_MTD/`**: Contains the core SDN implementation:
  * `totp_controller.py`: The Ryu SDN application managing the control and data planes.
  * `totp_engine.py`: The cryptographic engine responsible for generating the active window of OTPs.
  * `config.py`: The configuration file containing the shared cryptographic secrets, mutation intervals, and network IP references.

---

## 🛠️ Topology Setup

Before starting the SDN controller, you must initialize the emulated network environment.

1. **Cleanup the Network:** Ensure no previous Mininet processes or hanging links are active:

```bash
sudo mn -c
```

2. **Launch the Topology:** Navigate to the `network` directory and start the script:

```bash
sudo python3 topology.py
```

> **Note:** This script automatically initializes the following containerized nodes: `c1` (Authorized Client), `a1` (Attacker), `decoy` (Decoy Node), and `target` (Victim Server running an active Apache/Web application).

---

## 🧠 Controller Execution (Ryu)

Open a new terminal window, navigate to the `TOTP_MTD` directory, and launch the Ryu controller. 

This mode implements time-based TCP port mutation. It ensures that only nodes explicitly authorized and synchronized with the cryptographic secret can traverse the network. It is executed alongside the standard OpenFlow Layer 2 switching module to handle basic network traffic (ARP).

```bash
docker run -it --rm \
  --network host \
  -v "$(pwd):/app" \
  -w /app \
  -e PYTHONPATH=. \
  osrg/ryu \
  ryu-manager ryu.app.simple_switch_13 totp_controller.py
```

*You should see the controller logging the active MTD OTP ports every 30 seconds.*

---

## 🧪 Experiment Validation

Once the controller is active and pushing flow rules to the edge switches, you can perform the following tests within the active `containernet>` CLI.

### 1. Authorized Client Test (c1)

The client `c1` is structurally authorized by the SDN controller (via `config.py`). Its outbound traffic on port 80 is dynamically mutated by the edge switch, transported across the core, and restored before reaching the target.

```bash
containernet> c1 curl --connect-timeout 5 [http://10.0.0.3:80](http://10.0.0.3:80)
```

**Expected Result:** Success (HTML response from the Target Server received). The cryptographic translation is entirely transparent to the `curl` command.

### 2. Unauthorized Attacker Test (a1)

The attacker `a1` lacks an authorized network profile. The edge switch acting as the Restorer/Firewall (`s3`) will find no valid matching rules for the attacker's ingress traffic.

```bash
containernet> a1 curl --connect-timeout 5 [http://10.0.0.3:80](http://10.0.0.3:80)
```

**Expected Result:** `curl: (28) Connection timed out`. 

The packet is silently dropped by the `table-miss` rule on the edge switch (Stealth Firewall). The attacker receives no `TCP RST` or `ICMP` feedback, resulting in total topological blindness.

### 3. Port Scanning Isolation

You can further validate the defense by attempting an `nmap` scan from the attacker node:

```bash
containernet> a1 nmap -Pn -p 80 10.0.0.3
```

**Expected Result:** The port will show as `filtered` or the host will appear down, proving that standard reconnaissance tools are neutralized by the proactive mutation layer.