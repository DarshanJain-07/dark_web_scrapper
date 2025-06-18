# Stage 1: Build Stage
# Use a standard Python image to build our dependencies
FROM python:3.12-slim AS builder

# Set the working directory
WORKDIR /app

# Copy dependency files first (for caching)
COPY pyproject.toml poetry.lock* README.md ./

# Install dependencies (optional, but often done here)
RUN pip install --upgrade pip

# Copy the rest of the application code (including dark_web_scraper)
COPY . .

# Install the package in development mode
RUN pip install -e .

# Stage 2: Final Stage
# Use a fresh, clean Python image for the final container
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install system dependencies for Tor Browser and Firefox WebDriver
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    tar \
    xz-utils \
    libdbus-glib-1-2 \
    libxtst6 \
    ca-certificates \
    netcat-openbsd \
    libevent-2.1-7 \
    libssl3 \
    zlib1g \
    xvfb \
    firefox-esr \
    && rm -rf /var/lib/apt/lists/*

# Download and install geckodriver for Selenium
ARG GECKODRIVER_VERSION=0.34.0
RUN wget -q https://github.com/mozilla/geckodriver/releases/download/v${GECKODRIVER_VERSION}/geckodriver-v${GECKODRIVER_VERSION}-linux64.tar.gz && \
    tar -xzf geckodriver-v${GECKODRIVER_VERSION}-linux64.tar.gz && \
    mv geckodriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/geckodriver && \
    rm geckodriver-v${GECKODRIVER_VERSION}-linux64.tar.gz

# Download and install Tor Browser
ARG TBB_VERSION=14.5.3
ARG TBB_URL=https://www.torproject.org/dist/torbrowser/${TBB_VERSION}/tor-browser-linux-x86_64-${TBB_VERSION}.tar.xz
RUN wget -q ${TBB_URL} && \
    tar -xJf tor-browser-linux-x86_64-${TBB_VERSION}.tar.xz && \
    rm tor-browser-linux-x86_64-${TBB_VERSION}.tar.xz && \
    mv tor-browser /opt/tor-browser

# Copy the installed dependencies and executables from the builder stage
COPY --from=builder /usr/local /usr/local

# Copy the rest of the application code
COPY . .

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Command to run the scraper
CMD ["/entrypoint.sh"] 