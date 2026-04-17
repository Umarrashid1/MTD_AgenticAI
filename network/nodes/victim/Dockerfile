# Stage 1: Just borrow the files from Juice Shop
FROM bkimminich/juice-shop:latest AS source

# Stage 2: Use a standard Node environment that HAS a shell and apt-get
FROM node:18-slim

# Install tools (This is faster because node-slim is a known base)
RUN apt-get update && apt-get install -y \
    python3 \
    curl \
    nmap \
    iproute2 \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Create the directory
WORKDIR /juice-shop

# Copy ONLY the essential app files from the source image
# This is usually the part that takes a long time, so we copy the whole folder
COPY --from=source /juice-shop /juice-shop

EXPOSE 3000

# Start Juice Shop and keep container alive
CMD ["sh", "-c", "npm start & tail -f /dev/null"]