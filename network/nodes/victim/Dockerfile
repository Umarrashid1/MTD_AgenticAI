FROM node:20-slim

# 1. Install system tools and build essentials (needed to compile native modules)
RUN apt-get update && apt-get install -y \
    python3 \
    curl \
    nmap \
    iproute2 \
    iputils-ping \
    net-tools \
    procps \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Set up the app directory
WORKDIR /juice-shop

# 3. Copy EVERYTHING from the official image...
COPY --from=bkimminich/juice-shop:latest /juice-shop .

# ...but instantly delete the pre-compiled node_modules
RUN rm -rf node_modules

# 4. Reinstall dependencies to match the new OS and Node version
RUN npm install --omit=dev

EXPOSE 3000

# 5. Start the app
CMD ["npm", "start"]