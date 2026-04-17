FROM bkimminich/juice-shop:latest

USER root

# This installs the tools directly into the existing Juice Shop image
RUN apk update && apk add --no-cache \
    python3 \
    py3-pip \
    bash \
    curl \
    nmap \
    net-tools \
    iproute2 \
    iputils \
    bind-tools

WORKDIR /juice-shop

# Crucial: Ensure the 'node' user still owns the app files 
# so 'npm start' doesn't have permission issues.
RUN chown -R juice-shop:juice-shop /juice-shop

EXPOSE 3000

# We use 'sh -c' to ensure the background process starts correctly
CMD ["sh", "-c", "npm start & tail -f /dev/null"]