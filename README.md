# MTD_AgenticAI
This project implements a Moving Target Defense (MTD) mechanism using the Ryu SDN controller and a Docker-based network topology via Containernet.

## Project Structure
- `controller/`: Contains the Ryu application that implements the MTD logic.
- `network/`: Contains the Docker-based network topology and scripts to set up the environment.

## Setup Instructions
1. **Step 1: Start the Ryu Controller**
   - Activate ryu-env:
     ```bash
     source ryu-env/bin/activate
     ```
   - Run the Ryu application:
     ```bash
     ryu-manager controller/controller.py
     ```
2. **Step 2: Run Containernet**
   Note: We must use the specific python path to access containernet libraries
     ```bash
     sudo ~/containernet-env/bin/python network/topology.py
     ```
   