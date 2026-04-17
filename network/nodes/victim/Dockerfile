# Use the official Juice Shop base
FROM bkimminich/juice-shop

# Switch to root to install tools
USER root

# Alpine uses 'apk' instead of 'apt-get'
RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    git \
    net-tools \
    iproute2 \
    iputils \
    curl \
    nmap \
    netcat-openbsd \
    bind-tools \
    bash

# Set up the working directory (Juice Shop lives here by default)
WORKDIR /app

# Expose the port Juice Shop runs on
EXPOSE 3000

# Start Juice Shop in the background AND tail dev null to keep it alive for Containernet
# 'npm start' is the default start command for Juice Shop
CMD npm start & tail -f /dev/null