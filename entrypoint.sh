#!/bin/bash
set -e

# Start Xvfb for headless display
echo "Starting Xvfb display server..."
Xvfb :99 -screen 0 1024x768x24 -ac +extension GLX +render -noreset &
export DISPLAY=:99

# Wait for Xvfb to start
sleep 3

# Set additional environment variables for Firefox
export MOZ_HEADLESS=1
export FIREFOX_BINARY=/opt/tor-browser/Browser/firefox
export PATH="/usr/local/bin:$PATH"

# Start Tor daemon directly instead of using Tor Browser launcher
# This is more reliable in a headless environment
echo "Starting Tor daemon directly..."
/opt/tor-browser/Browser/TorBrowser/Tor/tor \
    --defaults-torrc /opt/tor-browser/Browser/TorBrowser/Data/Tor/torrc-defaults \
    --torrc-file /opt/tor-browser/Browser/TorBrowser/Data/Tor/torrc \
    --DataDirectory /opt/tor-browser/Browser/TorBrowser/Data/Tor \
    --SOCKSPort 9150 \
    --ControlPort 9151 \
    --CookieAuthentication 1 &

# Wait for Tor to start
sleep 10

# Wait for the SOCKS port to be open
echo "Waiting for Tor SOCKS port 9150 to be available..."
while ! nc -z localhost 9150; do
  sleep 1
done

echo "Tor SOCKS port is ready!"

# Test the Tor and Firefox WebDriver setup
echo "Testing Tor and Firefox WebDriver setup..."
python3 test_tor_connection.py

if [ $? -eq 0 ]; then
    echo "✓ Setup test passed. Starting the scraper..."
    # Run the scraper
    cd /app
    exec scrapy crawl tor_spider -a start_urls="${START_URLS}"
else
    echo "✗ Setup test failed. Please check the logs above."
    exit 1
fi