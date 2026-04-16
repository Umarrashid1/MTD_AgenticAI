# 🧠 Anatomy of the MTD Controller (Ryu SDN)

Think of your `main_controller.py` as the **Brain (Controller)** connected to the **Nervous System (the OpenFlow network)**. To understand it deeply, we will divide its operation into **4 Logical Phases**, following the exact life cycle of your network from the moment you press "Enter".

## 📚 Core Vocabulary
Before we begin, here are the fundamental terms used throughout the code:
* **`datapath`**: The software representation of a physical switch (e.g., `s1`, `s2`).
* **`ofproto`**: The dictionary of OpenFlow protocol rules (the constants).
* **`parser`**: The "translator" used to build OpenFlow messages to be sent to the switch.

---

## Phase 1: Awakening and Memory (Initialization)
As soon as you start the controller, the `__init__` function is executed. Here, the "brain" prepares its archives (dictionaries) and starts the engine.

* `self.mac_to_port`: **Spatial Memory**. It maps a MAC address to a physical switch port (e.g., *"The MAC of h1 is on Port 2"*).
* `self.ip_to_mac`: **Identity Memory**. It maps a Real IP to its TRUE physical MAC (e.g., *"IP 10.0.0.1 corresponds to NIC 00:...:01"*).
* `self.datapaths`: **The Phonebook**. It saves the ID of every connected switch.
* `hub.spawn(self._shuffling_loop)`: **Crucial**. Ryu creates a "Thread," a parallel process running in an infinite background loop. This is the **heartbeat** of your MTD.

---

## Phase 2: Recognition (Connection Events)
When you start Containernet, the switches (`s1`, `s2`, `s3`) power up and "call" the controller. This generates `ofp_event` events.

### 1. `_state_change_handler` (Event: `EventOFPStateChange`)
* **Trigger**: The exact moment the OpenFlow control cable connects or disconnects between a switch and the controller.
* **Action**: If the switch is "alive" (`MAIN_DISPATCHER`), it is added to the `self.datapaths` phonebook. If it "dies" (`DEAD_DISPATCHER`), it is removed.

### 2. `switch_features_handler` (Event: `EventOFPSwitchFeatures`)
* **Trigger**: Immediately after connection. This is the "handshake" where the switch asks: *"Hi, I'm s1, what should I do?"*
* **Action**: The controller installs the **Table-Miss flow entry** (Priority 0). This is the most important rule in SDN. It tells the switch: *"If you receive a packet you don't recognize, don't drop it! Send it to me (the Controller) for inspection."*

---

## Phase 3: The MTD Heartbeat (Background Loop)
While the network waits, the `_shuffling_loop` thread runs in the background.

* **The Wait**: `hub.sleep(interval)` puts the thread to sleep for a random duration (e.g., 30 seconds).
* **Amnesia**: Upon waking, it iterates through the phonebook (`self.datapaths`) and triggers `_clear_mtd_flows`. This deletes all old rules from the switches. The network "forgets" the past.
* **Unpacking**: `ip_map, port_map, mac_map = self.mtd_engine.shuffle_all()`
    The `shuffle_all()` function returns a package containing three dictionaries. We "unpack" these into 3 separate variables. Now we have the new cryptographic maps for **L2 (MAC)**, **L3 (IP)**, and **L4 (Ports)**.
* **The Megaphone**: It calls `_send_garps_for_all()`, which sends **Gratuitous ARPs** (broadcast messages with fake data) to all switches to notify the network of the identity change.

---

## Phase 4: Packet Inspection (`_packet_in_handler`)
This is the masterpiece—the **`EventOFPPacketIn`** event.



* **Trigger**: When a host sends a new packet and the switch (thanks to the Table-Miss rule) forwards it to the controller.

This function "unpacks the Russian dolls" of the packet (`msg.data`):

### A. Protocol Unpacking (`pkt.get_protocol`)
It takes the raw bits and transforms them into readable Python objects: `eth` (Layer 2), `pkt_ipv4` (Layer 3), `pkt_tcp` (Layer 4). If the packet is not IPv4, the variable `pkt_ipv4` will be `None`.

### B. The ARP Block (The Lying Gatekeeper)
If the packet is an ARP request seeking a **Virtual IP**, the controller stops everything (`return`). It calls `_handle_arp`, which **forges** a fake response packet using the **Virtual MAC** and sends it back. The attacker believes they have reached the host, but they have only spoken to the controller.

### C. The NAT Block (The Simultaneous Translator)
If it is a data packet (IPv4), it creates a list of `actions` (orders for the switch):
* **Inbound**: The packet has Destination = Virtual IP/MAC. The controller adds an order: *"Switch, use `SetField` to change the destination IP and MAC to the real ones, otherwise the server will never receive it."*
* **Outbound**: The packet has Source = Real IP/MAC. The controller adds an order: *"Switch, mask who is speaking. Replace the source with the virtual data."*

### D. L2 Forwarding Block (The Sorting)
Now that the packet is "translated," where do we send it? The controller checks `mac_to_port`. If it knows that the destination port is, for example, Port 3, it adds the order: *"Switch, forward the packet (`OFPActionOutput`) to Port 3."* If it doesn't know, it orders a **FLOOD** (send to all ports).

### E. Hardware Offloading (The Accelerator)
The controller doesn't want to repeat this logic for every subsequent packet in a stream.
* It creates a **match** (a condition: *"If Source IP is X and Dest IP is Y"*).
* It uses `self.add_flow` to send the complete rule to the switch: **Match + Actions**.
* From this moment on, the switch processes these packets at the **hardware level** (Priority 1), and the controller (Priority 0) is no longer disturbed until the next Shuffle clears the rules.

---

## Presentation Summary
If asked how the controller works during your presentation, you can summarize it as follows:

> "My Controller is based on a **reactive architecture**. It learns the topology and installs base rules via connection events. In the background, a thread periodically shuffles identities and sends ARP updates. In real-time, the **Packet-In** event intercepts unknown traffic, applies a **bidirectional translation (NAT)** of encrypted identities, and installs hardware rules to ensure high performance."