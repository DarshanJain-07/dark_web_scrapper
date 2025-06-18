#!/usr/bin/env python3
"""
Test script to verify Tor connection and Firefox WebDriver functionality.
This script can be run inside the container to test the setup.
"""

import time
import socket
import logging
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_tor_connection(socks_port=9150):
    """Test if Tor SOCKS proxy is available"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', socks_port))
        sock.close()
        if result == 0:
            logging.info(f"✓ Tor SOCKS proxy is available on port {socks_port}")
            return True
        else:
            logging.error(f"✗ Tor SOCKS proxy is not available on port {socks_port}")
            return False
    except Exception as e:
        logging.error(f"✗ Error testing Tor connection: {e}")
        return False

def test_firefox_webdriver():
    """Test Firefox WebDriver with Tor proxy"""
    try:
        # Configure Firefox options
        firefox_options = Options()
        firefox_options.add_argument('--headless')
        firefox_options.add_argument('--no-sandbox')
        firefox_options.add_argument('--disable-dev-shm-usage')
        
        # Set Firefox binary path
        firefox_binary_path = "/opt/tor-browser/Browser/firefox"
        firefox_options.binary_location = firefox_binary_path
        
        # Configure Tor SOCKS proxy
        firefox_options.set_preference("network.proxy.type", 1)
        firefox_options.set_preference("network.proxy.socks", "127.0.0.1")
        firefox_options.set_preference("network.proxy.socks_port", 9150)
        firefox_options.set_preference("network.proxy.socks_version", 5)
        firefox_options.set_preference("network.proxy.socks_remote_dns", True)
        
        # Additional preferences
        firefox_options.set_preference("browser.cache.disk.enable", False)
        firefox_options.set_preference("browser.cache.memory.enable", False)

        # Disable HTTPS-only mode and other security features that might interfere
        firefox_options.set_preference("dom.security.https_only_mode", False)
        firefox_options.set_preference("dom.security.https_only_mode_pbm", False)
        firefox_options.set_preference("security.tls.insecure_fallback_hosts", "httpbin.org")
        firefox_options.set_preference("network.stricttransportsecurity.preloadlist", False)
        firefox_options.set_preference("security.mixed_content.block_active_content", False)
        firefox_options.set_preference("security.mixed_content.block_display_content", False)

        # Disable Tor Launcher prompts and dialogs
        firefox_options.set_preference("extensions.torlauncher.start_tor", False)
        firefox_options.set_preference("extensions.torlauncher.prompt_at_startup", False)
        firefox_options.set_preference("browser.shell.checkDefaultBrowser", False)
        firefox_options.set_preference("browser.tabs.warnOnClose", False)
        firefox_options.set_preference("browser.sessionstore.resume_from_crash", False)
        
        # Create service
        service = Service()
        
        # Initialize WebDriver
        logging.info("Initializing Firefox WebDriver...")
        driver = webdriver.Firefox(options=firefox_options, service=service)
        driver.set_page_load_timeout(30)
        
        logging.info("✓ Firefox WebDriver initialized successfully")
        
        # Test basic functionality by loading a simple page
        logging.info("Testing basic WebDriver functionality...")
        driver.get("about:blank")
        time.sleep(2)

        # Get page title to verify WebDriver is working
        title = driver.title
        logging.info(f"✓ Successfully loaded page. Title: '{title}'")
        logging.info("✓ Firefox WebDriver is working correctly with Tor proxy")
        
        # Clean up
        driver.quit()
        logging.info("✓ Firefox WebDriver closed successfully")
        return True
        
    except Exception as e:
        logging.error(f"✗ Error testing Firefox WebDriver: {e}")
        return False

def main():
    """Run all tests"""
    logging.info("Starting Tor and Firefox WebDriver tests...")
    
    # Test 1: Tor connection
    tor_ok = test_tor_connection()
    
    if not tor_ok:
        logging.error("Tor connection test failed. Cannot proceed with WebDriver test.")
        return False
    
    # Test 2: Firefox WebDriver
    webdriver_ok = test_firefox_webdriver()
    
    if tor_ok and webdriver_ok:
        logging.info("🎉 All tests passed! The setup is working correctly.")
        return True
    else:
        logging.error("❌ Some tests failed. Please check the configuration.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
