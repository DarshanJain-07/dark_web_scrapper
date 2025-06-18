import scrapy
from scrapy.linkextractors import LinkExtractor
from ..items import ScrapedDataItem
import logging
from urllib.parse import urlparse
from datetime import datetime
from scrapy.exceptions import IgnoreRequest

class TorSpider(scrapy.Spider):
    name = 'tor_spider'

    # Custom settings for retry handling
    custom_settings = {
        'RETRY_TIMES': 3,  # Maximum retry attempts
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429, 400, 403, 404, 405],
        'DOWNLOAD_TIMEOUT': 60,  # Timeout for each request
        'DOWNLOAD_DELAY': 2,  # Delay between requests
        'RANDOMIZE_DOWNLOAD_DELAY': 0.5,  # Randomize delay (0.5 * to 1.5 * DOWNLOAD_DELAY)
    }

    def __init__(self, *args, **kwargs):
        super(TorSpider, self).__init__(*args, **kwargs)
        # Track failed URLs to avoid infinite retries
        self.failed_urls = set()
        # Track retry counts per URL
        self.retry_counts = {}

    def start_requests(self):
        if not hasattr(self, 'start_urls') or not self.start_urls:
            logging.error("No start_urls provided! Use -a start_urls='http://url1.onion,http://url2.onion'")
            return
        
        # Accept comma-separated URLs
        urls = self.start_urls.split(',')
        
        # Set allowed_domains from start_urls if not explicitly provided
        if not hasattr(self, 'allowed_domains'):
            self.allowed_domains = {urlparse(url).netloc for url in urls}
            logging.info(f"Automatically configured allowed_domains: {self.allowed_domains}")

        for url in urls:
            yield scrapy.Request(
                url,
                self.parse,
                meta={'selenium': True},
                errback=self.handle_error,
                dont_filter=False
            )

    def parse(self, response):
        logging.info(f"Parsing page: {response.url}")

        item = ScrapedDataItem()
        item['url'] = response.url
        texts = response.xpath('//body//text()[not(parent::script) and not(parent::style)]').getall()
        item['text_content'] = " ".join(text.strip() for text in texts if text.strip())
        item['html_content'] = response.body.decode(response.encoding, 'ignore')
        item['timestamp'] = datetime.utcnow()
        yield item

        link_extractor = LinkExtractor(allow_domains=self.allowed_domains, unique=True)
        links = link_extractor.extract_links(response)
        logging.info(f"Found {len(links)} links on {response.url}")

        for link in links:
            # Skip URLs that have already failed multiple times
            if link.url in self.failed_urls:
                logging.info(f"Skipping previously failed URL: {link.url}")
                continue

            logging.debug(f"Following link: {link.url}")
            yield scrapy.Request(
                link.url,
                self.parse,
                meta={'selenium': True},
                errback=self.handle_error,
                dont_filter=False
            )

    def handle_error(self, failure):
        """Handle request failures and implement retry logic"""
        request = failure.request
        url = request.url

        # Increment retry count for this URL
        self.retry_counts[url] = self.retry_counts.get(url, 0) + 1

        logging.error(f"Request failed for {url}: {failure.value}")
        logging.info(f"Retry count for {url}: {self.retry_counts[url]}")

        # If we've exceeded max retries, mark URL as failed
        if self.retry_counts[url] >= self.custom_settings['RETRY_TIMES']:
            self.failed_urls.add(url)
            logging.warning(f"URL {url} marked as dead after {self.retry_counts[url]} failed attempts")
            return

        # Otherwise, retry the request with a delay
        logging.info(f"Retrying {url} (attempt {self.retry_counts[url] + 1})")
        yield scrapy.Request(
            url,
            self.parse,
            meta={'selenium': True},
            errback=self.handle_error,
            dont_filter=True  # Allow retry of the same URL
        )
