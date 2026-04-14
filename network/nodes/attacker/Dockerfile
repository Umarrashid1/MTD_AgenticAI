FROM kalilinux/kali-rolling
LABEL authors="umarrashid"
ENV DEBIAN_FRONTEND=noninteractive

# Update Kali and install Python alongside essential networking/hacking tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    git \
    net-tools \
    iproute2 \
    iputils-ping \
    curl \
    nmap \
    netcat-traditional \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Set up the working directory
WORKDIR /app

# Create a virtual environment for Python
# Setting the PATH ensures the venv is always "activated"
ENV VIRTUAL_ENV=/app/cai_env
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install the CAI framework
RUN pip install --no-cache-dir cai-framework

# --- CAI & OLLAMA CONFIGURATION ---
# Point CAI to the Ollama instance running on your Ubuntu Host!
ENV CAI_MODEL="ollama/DeepHat"
ENV OPENAI_API_BASE="http://172.17.0.1:11434"
# (LiteLLM, which CAI uses under the hood, looks for the OPENAI_API_BASE
# variable to route traffic, even when talking to Ollama)

# Containernet requires the container to stay alive.
CMD ["tail", "-f", "/dev/null"]