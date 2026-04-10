FROM ubuntu:24.04
LABEL authors="umarrashid"
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    git \
    net-tools \
    iproute2 \
    iputils-ping \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up the working directory
WORKDIR /app

# Create a virtual environment for Python 3.12
# Setting the PATH ensures the venv is always "activated" for subsequent RUN and CMD commands
ENV VIRTUAL_ENV=/app/cai_env
RUN python3.12 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install the CAI framework
RUN pip install --no-cache-dir cai-framework


# Containernet requires the container to stay alive.
# Starting a bash shell keeps the container running so Containernet can execute commands inside it.
CMD ["/bin/bash"]