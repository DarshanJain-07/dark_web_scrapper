from opensearchpy import OpenSearch, RequestsHttpConnection, exceptions
from .items import ScrapedDataItem
import logging
import time

class OpenSearchPipeline:
    """
    This pipeline takes scraped items and indexes them into OpenSearch.
    It handles the connection to the database and creates the index if it
    does not already exist.
    """

    def __init__(self, opensearch_host, opensearch_port, opensearch_index, opensearch_user, opensearch_password):
        self.opensearch_host = opensearch_host
        self.opensearch_port = opensearch_port
        self.opensearch_index = opensearch_index
        self.opensearch_user = opensearch_user
        self.opensearch_password = opensearch_password
        self.client = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            opensearch_host=crawler.settings.get('OPENSEARCH_HOST'),
            opensearch_port=crawler.settings.get('OPENSEARCH_PORT'),
            opensearch_index=crawler.settings.get('OPENSEARCH_INDEX'),
            opensearch_user=crawler.settings.get('OPENSEARCH_USER'),
            opensearch_password=crawler.settings.get('OPENSEARCH_PASSWORD'),
        )

    def open_spider(self, spider):
        """
        Connect to OpenSearch and create the index if it doesn't exist.
        Includes a retry mechanism to handle race conditions during startup.
        """
        retries = 5
        delay = 10  # seconds
        for i in range(retries):
            try:
                self.client = OpenSearch(
                    hosts=[{'host': self.opensearch_host, 'port': self.opensearch_port}],
                    http_auth=(self.opensearch_user, self.opensearch_password),
                    use_ssl=True,
                    verify_certs=False,  # Using self-signed certificates
                    ssl_show_warn=False,  # Suppress SSL warnings for self-signed certs
                    connection_class=RequestsHttpConnection,
                    timeout=30, # Connection timeout
                )
                # The health check ensures the cluster is up, but we also ping here
                # to be certain the node is ready for connections.
                if self.client.ping():
                    logging.info("Successfully connected to OpenSearch")
                    self._create_index_if_not_exists()
                    return
                else:
                    logging.warning("OpenSearch ping failed. Retrying...")
            except exceptions.ConnectionError as e:
                logging.warning(f"Could not connect to OpenSearch (attempt {i+1}/{retries}): {e}. Retrying in {delay}s...")
            
            time.sleep(delay)
        
        logging.error("Failed to connect to OpenSearch after multiple retries. Shutting down spider.")
        raise Exception("Failed to connect to OpenSearch after multiple retries")


    def _create_index_if_not_exists(self):
        """
        Creates the OpenSearch index with a specific mapping if it doesn't already exist.
        """
        if not self.client.indices.exists(index=self.opensearch_index):
            mapping = {
                "mappings": {
                    "properties": {
                        "url": {"type": "keyword"},
                        "text_content": {"type": "text"},
                        "html_content": {"type": "text", "index": False},
                        "timestamp": {"type": "date"}
                    }
                }
            }
            self.client.indices.create(index=self.opensearch_index, body=mapping)
            logging.info(f"Created OpenSearch index: {self.opensearch_index}")

    def process_item(self, item, spider):
        """
        Index the scraped item into OpenSearch.
        """
        if isinstance(item, ScrapedDataItem):
            try:
                self.client.index(
                    index=self.opensearch_index,
                    body={
                        "url": item["url"],
                        "text_content": item["text_content"],
                        "html_content": item["html_content"],
                        "timestamp": item["timestamp"],
                    },
                )
                logging.info(f"Successfully indexed item from {item['url']}")
            except Exception as e:
                logging.error(f"Failed to index item from {item['url']}: {e}")
        return item

    def close_spider(self, spider):
        # Clean up the connection
        if self.client:
            self.client.close()
            logging.info("OpenSearch connection closed") 