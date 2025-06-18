"""
OpenSearch client for connecting to the scraped data storage.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
import urllib3
from opensearchpy import OpenSearch
from opensearchpy.exceptions import ConnectionError, NotFoundError, RequestError

from .config import Settings
from .models import ScrapedDocument

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """Client for interacting with OpenSearch."""
    
    def __init__(self, settings: Settings):
        """Initialize OpenSearch client."""
        self.settings = settings
        self.index_name = settings.opensearch_index
        
        # OpenSearch client configuration
        self.client_config = {
            'hosts': [f"{settings.opensearch_scheme}://{settings.opensearch_host}:{settings.opensearch_port}"],
            'http_auth': (settings.opensearch_user, settings.opensearch_password),
            'use_ssl': settings.opensearch_scheme == 'https',
            'verify_certs': settings.opensearch_verify_certs,
            'ssl_show_warn': settings.opensearch_ssl_show_warn,
            'timeout': settings.search_timeout,
        }
        
        # Create synchronous client
        self.client = OpenSearch(**self.client_config)
        
        logger.info(f"OpenSearch client initialized for {settings.opensearch_host}:{settings.opensearch_port}")
    
    async def health_check(self) -> bool:
        """Check if OpenSearch is healthy and accessible."""
        try:
            # Use synchronous client for health check
            health = self.client.cluster.health()
            return health.get('status') in ['green', 'yellow']
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the scraped data."""
        try:
            # Get document count
            count_response = self.client.count(index=self.index_name)
            total_documents = count_response.get('count', 0)
            
            # Get unique URLs count and date range
            aggs_query = {
                "size": 0,
                "aggs": {
                    "unique_urls": {
                        "cardinality": {
                            "field": "url.keyword"
                        }
                    },
                    "date_range": {
                        "stats": {
                            "field": "timestamp"
                        }
                    }
                }
            }
            
            aggs_response = self.client.search(index=self.index_name, body=aggs_query)
            aggregations = aggs_response.get('aggregations', {})
            
            unique_urls = aggregations.get('unique_urls', {}).get('value', 0)
            date_stats = aggregations.get('date_range', {})
            
            # Get index size
            index_stats = self.client.indices.stats(index=self.index_name)
            index_size_bytes = index_stats.get('indices', {}).get(self.index_name, {}).get('total', {}).get('store', {}).get('size_in_bytes', 0)
            index_size = self._format_bytes(index_size_bytes)
            
            # Convert timestamps
            latest_scrape = None
            oldest_scrape = None
            
            if date_stats.get('max'):
                latest_scrape = datetime.fromtimestamp(date_stats['max'] / 1000)
            if date_stats.get('min'):
                oldest_scrape = datetime.fromtimestamp(date_stats['min'] / 1000)
            
            return {
                'total_documents': total_documents,
                'unique_urls': unique_urls,
                'latest_scrape': latest_scrape,
                'oldest_scrape': oldest_scrape,
                'index_size': index_size
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise
    
    async def search_documents(
        self,
        query: str,
        page: int = 1,
        size: int = 20,
        sort_field: str = "_score",
        sort_order: str = "desc",
        include_html: bool = False
    ) -> Tuple[List[ScrapedDocument], int, int]:
        """Search documents by query string."""
        try:
            # Calculate offset
            offset = (page - 1) * size
            
            # Build search query
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["text_content", "url"],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                },
                "sort": [
                    {sort_field: {"order": sort_order}}
                ],
                "from": offset,
                "size": size,
                "_source": self._get_source_fields(include_html)
            }
            
            response = self.client.search(index=self.index_name, body=search_body)
            
            # Parse results
            documents = []
            for hit in response['hits']['hits']:
                doc = self._parse_document(hit, include_score=True)
                documents.append(doc)
            
            total = response['hits']['total']['value']
            took = response['took']
            
            return documents, total, took
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def get_all_documents(
        self,
        page: int = 1,
        size: int = 20,
        sort_field: str = "timestamp",
        sort_order: str = "desc",
        include_html: bool = False
    ) -> Tuple[List[ScrapedDocument], int]:
        """Get all documents with pagination."""
        try:
            # Calculate offset
            offset = (page - 1) * size
            
            # Build query
            search_body = {
                "query": {"match_all": {}},
                "sort": [
                    {sort_field: {"order": sort_order}}
                ],
                "from": offset,
                "size": size,
                "_source": self._get_source_fields(include_html)
            }
            
            response = self.client.search(index=self.index_name, body=search_body)
            
            # Parse results
            documents = []
            for hit in response['hits']['hits']:
                doc = self._parse_document(hit)
                documents.append(doc)
            
            total = response['hits']['total']['value']
            
            return documents, total
            
        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            raise
    
    async def get_document_by_url(self, url: str, include_html: bool = False) -> Optional[ScrapedDocument]:
        """Get a specific document by URL."""
        try:
            search_body = {
                "query": {
                    "term": {
                        "url.keyword": url
                    }
                },
                "size": 1,
                "_source": self._get_source_fields(include_html)
            }
            
            response = self.client.search(index=self.index_name, body=search_body)
            
            if response['hits']['total']['value'] > 0:
                hit = response['hits']['hits'][0]
                return self._parse_document(hit)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document by URL: {e}")
            raise
    
    async def get_urls(self, page: int = 1, size: int = 20) -> Tuple[List[str], int]:
        """Get list of all scraped URLs."""
        try:
            # Calculate offset
            offset = (page - 1) * size
            
            search_body = {
                "query": {"match_all": {}},
                "sort": [{"timestamp": {"order": "desc"}}],
                "from": offset,
                "size": size,
                "_source": ["url"]
            }
            
            response = self.client.search(index=self.index_name, body=search_body)
            
            urls = [hit['_source']['url'] for hit in response['hits']['hits']]
            total = response['hits']['total']['value']
            
            return urls, total
            
        except Exception as e:
            logger.error(f"Failed to get URLs: {e}")
            raise
    
    def _get_source_fields(self, include_html: bool) -> List[str]:
        """Get source fields to include in response."""
        fields = ["url", "text_content", "timestamp"]
        if include_html:
            fields.append("html_content")
        return fields
    
    def _parse_document(self, hit: Dict[str, Any], include_score: bool = False) -> ScrapedDocument:
        """Parse OpenSearch hit into ScrapedDocument."""
        source = hit['_source']
        
        # Parse timestamp
        timestamp_str = source.get('timestamp')
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            timestamp = datetime.utcnow()
        
        doc_data = {
            'id': hit['_id'],
            'url': source.get('url', ''),
            'text_content': source.get('text_content', ''),
            'html_content': source.get('html_content'),
            'timestamp': timestamp
        }
        
        if include_score and '_score' in hit:
            doc_data['score'] = hit['_score']
        
        return ScrapedDocument(**doc_data)
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes into human readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"
