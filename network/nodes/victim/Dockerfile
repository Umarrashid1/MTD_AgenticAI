# Stage 1: Get the Juice Shop files
FROM bkimminich/juice-shop:latest AS source

# Stage 2: Build our functional victim container
FROM node:18-bookworm-slim

# Install your networking and security tools
# We use apt-get here because bookworm-slim is Debian-based
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    net-tools \
    iproute2 \
    iputils-ping \
    curl \
    nmap \
    netcat-traditional \
    dnsutils \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the application from the official image to this one
COPY --from=source /app /app

# Juice Shop needs to run as a specific user for some features,
# but for a lab 'root' is fine, or you can create one.
EXPOSE 3000

# Start Juice Shop and keep the container open for Containernet
CMD npm start & tail -f /dev/null