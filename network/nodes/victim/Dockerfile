# Stage 1: Get the Juice Shop files
FROM bkimminich/juice-shop:latest AS source

# Stage 2: Build our functional victim container
FROM node:18-bookworm-slim

# Install your networking and security tools
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
WORKDIR /juice-shop

# Copy the application from the official image (using the correct path)
COPY --from=source /juice-shop /juice-shop

# Fix permissions so the app can write to its local database if needed
RUN chown -R node:node /juice-shop

EXPOSE 3000

# Start Juice Shop and keep the container open for Containernet
CMD npm start & tail -f /dev/null