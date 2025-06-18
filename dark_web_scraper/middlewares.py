import logging
import time
import socket
from scrapy import signals
from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.common.exceptions import TimeoutException, WebDriverException
from scrapy.exceptions import IgnoreRequest

class SeleniumMiddleware:
    """
    This Scrapy middleware uses Selenium with Firefox to fetch pages through Tor.
    It's designed to handle requests that have meta['selenium'] = True.
    Uses regular Firefox WebDriver with Tor SOCKS proxy for better container compatibility.
    """

    def __init__(self, tbb_path, socks_port=9150, control_port=9151):
        self.tbb_path = tbb_path
        self.socks_port = socks_port
        self.control_port = control_port
        self.driver = None
        self.crawler = None

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        middleware = cls(
            tbb_path=crawler.settings.get('TBB_PATH'),
            socks_port=crawler.settings.get('TOR_SOCKS_PORT', 9150),
            control_port=crawler.settings.get('TOR_CONTROL_PORT', 9151)
        )
        middleware.crawler = crawler
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def _wait_for_tor(self, max_attempts=30):
        """Wait for Tor SOCKS proxy to be available"""
        for attempt in range(max_attempts):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', self.socks_port))
                sock.close()
                if result == 0:
                    logging.info(f"Tor SOCKS proxy is available on port {self.socks_port}")
                    return True
            except Exception as e:
                logging.debug(f"Attempt {attempt + 1}: Tor not ready yet - {e}")
            time.sleep(2)
        return False

    def spider_opened(self, spider):
        try:
            # Wait for Tor to be available
            if not self._wait_for_tor():
                raise Exception("Tor SOCKS proxy is not available after waiting")

            # Configure Firefox options for headless operation with Tor
            firefox_options = Options()
            firefox_options.add_argument('--headless')
            firefox_options.add_argument('--no-sandbox')
            firefox_options.add_argument('--disable-dev-shm-usage')
            firefox_options.add_argument('--disable-gpu')
            firefox_options.add_argument('--disable-extensions')
            firefox_options.add_argument('--disable-plugins')
            firefox_options.add_argument('--disable-images')

            # Set Firefox binary path
            firefox_binary_path = f"{self.tbb_path}/Browser/firefox"
            firefox_options.binary_location = firefox_binary_path

            # Configure Tor SOCKS proxy
            firefox_options.set_preference("network.proxy.type", 1)  # Manual proxy
            firefox_options.set_preference("network.proxy.socks", "127.0.0.1")
            firefox_options.set_preference("network.proxy.socks_port", self.socks_port)
            firefox_options.set_preference("network.proxy.socks_version", 5)
            firefox_options.set_preference("network.proxy.socks_remote_dns", True)

            # Additional privacy and performance preferences
            firefox_options.set_preference("browser.cache.disk.enable", False)
            firefox_options.set_preference("browser.cache.memory.enable", False)
            firefox_options.set_preference("browser.cache.offline.enable", False)
            firefox_options.set_preference("network.http.use-cache", False)
            firefox_options.set_preference("media.volume_scale", "0.0")
            firefox_options.set_preference("dom.webnotifications.enabled", False)
            firefox_options.set_preference("dom.push.enabled", False)
            firefox_options.set_preference("browser.startup.homepage", "about:blank")
            firefox_options.set_preference("startup.homepage_welcome_url", "about:blank")

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

            # Create Firefox service
            service = Service()

            # Initialize the WebDriver
            self.driver = webdriver.Firefox(options=firefox_options, service=service)
            self.driver.set_page_load_timeout(60)

            logging.info("Firefox WebDriver with Tor proxy initialized successfully")

            # Test the connection by checking IP
            try:
                self.driver.get("http://httpbin.org/ip")
                time.sleep(3)
                logging.info("Tor connection test completed")
            except Exception as e:
                logging.warning(f"Tor connection test failed: {e}")

        except Exception as e:
            logging.error(f"Failed to initialize Firefox WebDriver with Tor: {e}")
            # In case of failure, it's critical to stop the crawl
            # to prevent further errors.
            if self.crawler:
                self.crawler.engine.close_spider(spider, 'webdriver_init_failed')

    def process_request(self, request, spider):
        # We only process requests that are explicitly marked for Selenium
        if not request.meta.get('selenium'):
            return None

        if not self.driver:
            logging.error("Firefox WebDriver not initialized. Request cannot be processed.")
            raise IgnoreRequest(f"WebDriver not available for {request.url}")

        try:
            # Set a shorter timeout for .onion sites that might be down
            self.driver.set_page_load_timeout(30)

            logging.info(f"Loading URL: {request.url}")
            self.driver.get(request.url)

            # Wait for body element with shorter timeout for dead sites
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
            except TimeoutException:
                logging.warning(f"Timeout waiting for body element on {request.url}")
                # Still try to get the page source in case something loaded
                pass

            # Give some time for content to load
            time.sleep(2)

            body = self.driver.page_source
            current_url = self.driver.current_url

            # Check if we got redirected to an error page
            if "about:neterror" in current_url or "connection failure" in body.lower():
                logging.error(f"Connection failure detected for {request.url}")
                raise IgnoreRequest(f"Connection failure for {request.url}")

            # Check if we got minimal content (likely a dead site)
            if len(body.strip()) < 100:
                logging.warning(f"Minimal content received from {request.url}")
                raise IgnoreRequest(f"Minimal content from {request.url}")

            logging.info(f"Successfully loaded {request.url} ({len(body)} characters)")

            # Return an HtmlResponse so Scrapy can parse it
            return HtmlResponse(
                current_url,
                body=body,
                encoding='utf-8',
                request=request
            )

        except TimeoutException as e:
            logging.error(f"Timeout loading {request.url}: {e}")
            raise IgnoreRequest(f"Timeout for {request.url}")

        except WebDriverException as e:
            logging.error(f"WebDriver error for {request.url}: {e}")
            raise IgnoreRequest(f"WebDriver error for {request.url}")

        except Exception as e:
            logging.error(f"Unexpected error processing {request.url}: {e}")
            raise IgnoreRequest(f"Unexpected error for {request.url}")

    def spider_closed(self, spider):
        # Ensure the driver is closed when the spider is finished
        if self.driver:
            self.driver.quit()
            logging.info("Firefox WebDriver closed.")