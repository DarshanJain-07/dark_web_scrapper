#!/usr/bin/env python3
"""
Smart deduplication system for the Dark Web Scraper.

This module provides efficient duplicate detection during scraping:
1. Bloom filter for fast URL checking
2. Redis-based URL cache for distributed scraping
3. Database-backed URL checking for accuracy
4. Configurable deduplication strategies
"""

import os
import hashlib
import time
from typing import Set, Optional, List
from datetime import datetime, timedelta
import json
import redis
from opensearchpy import OpenSearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BloomFilter:
    """Simple Bloom filter implementation for fast URL checking."""
    
    def __init__(self, capacity: int = 1000000, error_rate: float = 0.1):
        """Initialize Bloom filter with given capacity and error rate."""
        import math
        
        # Calculate optimal parameters
        self.capacity = capacity
        self.error_rate = error_rate
        
        # Calculate bit array size
        self.bit_array_size = int(-capacity * math.log(error_rate) / (math.log(2) ** 2))
        
        # Calculate number of hash functions
        self.hash_count = int(self.bit_array_size * math.log(2) / capacity)
        
        # Initialize bit array
        self.bit_array = [0] * self.bit_array_size
        
        print(f"🔍 Bloom filter initialized: {self.bit_array_size} bits, {self.hash_count} hash functions")
    
    def _hash(self, item: str, seed: int) -> int:
        """Generate hash for item with given seed."""
        hash_obj = hashlib.md5(f"{item}{seed}".encode())
        return int(hash_obj.hexdigest(), 16) % self.bit_array_size
    
    def add(self, item: str):
        """Add item to Bloom filter."""
        for i in range(self.hash_count):
            index = self._hash(item, i)
            self.bit_array[index] = 1
    
    def contains(self, item: str) -> bool:
        """Check if item might be in the set (may have false positives)."""
        for i in range(self.hash_count):
            index = self._hash(item, i)
            if self.bit_array[index] == 0:
                return False
        return True
    
    def save_to_file(self, filename: str):
        """Save Bloom filter to file."""
        data = {
            'capacity': self.capacity,
            'error_rate': self.error_rate,
            'bit_array_size': self.bit_array_size,
            'hash_count': self.hash_count,
            'bit_array': self.bit_array
        }
        with open(filename, 'w') as f:
            json.dump(data, f)
    
    @classmethod
    def load_from_file(cls, filename: str) -> 'BloomFilter':
        """Load Bloom filter from file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        bloom = cls(data['capacity'], data['error_rate'])
        bloom.bit_array_size = data['bit_array_size']
        bloom.hash_count = data['hash_count']
        bloom.bit_array = data['bit_array']
        return bloom


class SmartDeduplicator:
    """Smart deduplication system with multiple strategies."""
    
    def __init__(self, strategy: str = "bloom_and_db", redis_url: Optional[str] = None):
        """Initialize deduplicator with chosen strategy."""
        self.strategy = strategy
        self.bloom_filter = None
        self.redis_client = None
        self.opensearch_client = None
        self.url_cache = set()
        
        # Initialize based on strategy
        if "bloom" in strategy:
            self._init_bloom_filter()
        
        if "redis" in strategy and redis_url:
            self._init_redis(redis_url)
        
        if "db" in strategy:
            self._init_opensearch()
        
        print(f"🚀 Smart deduplicator initialized with strategy: {strategy}")
    
    def _init_bloom_filter(self):
        """Initialize Bloom filter."""
        bloom_file = "url_bloom_filter.json"
        
        if os.path.exists(bloom_file):
            try:
                self.bloom_filter = BloomFilter.load_from_file(bloom_file)
                print("📂 Loaded existing Bloom filter")
            except:
                print("⚠️ Failed to load Bloom filter, creating new one")
                self.bloom_filter = BloomFilter()
        else:
            self.bloom_filter = BloomFilter()
    
    def _init_redis(self, redis_url: str):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()
            print("✅ Redis connection established")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}")
            self.redis_client = None
    
    def _init_opensearch(self):
        """Initialize OpenSearch connection."""
        try:
            self.opensearch_client = OpenSearch(
                hosts=[f"https://{os.getenv('OPENSEARCH_HOST', 'localhost')}:9200"],
                http_auth=(
                    os.getenv('OPENSEARCH_SCRAPER_USER'),
                    os.getenv('OPENSEARCH_SCRAPER_PASSWORD')
                ),
                use_ssl=True,
                verify_certs=False,
                ssl_show_warn=False,
                timeout=10
            )
            print("✅ OpenSearch connection established")
        except Exception as e:
            print(f"⚠️ OpenSearch connection failed: {e}")
            self.opensearch_client = None
    
    def load_existing_urls(self):
        """Load existing URLs from database into cache/bloom filter."""
        if not self.opensearch_client:
            return
        
        print("📥 Loading existing URLs from database...")
        
        try:
            # Query for all URLs
            query = {
                "size": 10000,
                "_source": ["url"],
                "query": {"match_all": {}}
            }
            
            response = self.opensearch_client.search(
                index=os.getenv("OPENSEARCH_INDEX", "darkweb-content"),
                body=query
            )
            
            urls = set()
            for hit in response['hits']['hits']:
                url = hit['_source'].get('url')
                if url:
                    urls.add(url)
                    
                    # Add to bloom filter
                    if self.bloom_filter:
                        self.bloom_filter.add(url)
                    
                    # Add to Redis cache
                    if self.redis_client:
                        self.redis_client.sadd("scraped_urls", url)
            
            self.url_cache = urls
            print(f"📊 Loaded {len(urls)} existing URLs")
            
            # Save bloom filter
            if self.bloom_filter:
                self.bloom_filter.save_to_file("url_bloom_filter.json")
            
        except Exception as e:
            print(f"❌ Failed to load existing URLs: {e}")
    
    def is_url_scraped(self, url: str) -> bool:
        """Check if URL has already been scraped."""
        # Strategy 1: Bloom filter (fast, may have false positives)
        if "bloom" in self.strategy and self.bloom_filter:
            if not self.bloom_filter.contains(url):
                return False  # Definitely not scraped
        
        # Strategy 2: Redis cache (fast, accurate for recent URLs)
        if "redis" in self.strategy and self.redis_client:
            try:
                if self.redis_client.sismember("scraped_urls", url):
                    return True
            except:
                pass
        
        # Strategy 3: Local cache (fast, accurate for current session)
        if url in self.url_cache:
            return True
        
        # Strategy 4: Database check (slow, but accurate)
        if "db" in self.strategy and self.opensearch_client:
            return self._check_url_in_database(url)
        
        return False
    
    def _check_url_in_database(self, url: str) -> bool:
        """Check if URL exists in database."""
        try:
            query = {
                "query": {
                    "term": {
                        "url.keyword": url
                    }
                },
                "size": 1
            }
            
            response = self.opensearch_client.search(
                index=os.getenv("OPENSEARCH_INDEX", "darkweb-content"),
                body=query
            )
            
            return response['hits']['total']['value'] > 0
            
        except Exception as e:
            print(f"⚠️ Database check failed for {url}: {e}")
            return False
    
    def mark_url_scraped(self, url: str):
        """Mark URL as scraped in all caches."""
        # Add to local cache
        self.url_cache.add(url)
        
        # Add to bloom filter
        if self.bloom_filter:
            self.bloom_filter.add(url)
        
        # Add to Redis cache
        if self.redis_client:
            try:
                self.redis_client.sadd("scraped_urls", url)
                # Set expiration for Redis entries (optional)
                self.redis_client.expire("scraped_urls", 86400 * 7)  # 7 days
            except:
                pass
    
    def filter_new_urls(self, urls: List[str]) -> List[str]:
        """Filter list of URLs to only include new ones."""
        new_urls = []
        
        for url in urls:
            if not self.is_url_scraped(url):
                new_urls.append(url)
                # Pre-mark as scraped to avoid duplicates in same batch
                self.mark_url_scraped(url)
        
        print(f"🔍 Filtered {len(urls)} URLs -> {len(new_urls)} new URLs")
        return new_urls
    
    def cleanup_old_entries(self, days: int = 30):
        """Clean up old entries from caches."""
        if self.redis_client:
            try:
                # Clean up old Redis entries
                cutoff_time = time.time() - (days * 86400)
                # This would require storing timestamps with URLs
                # For simplicity, we'll just clear the cache periodically
                print("🧹 Cleaning up Redis cache...")
                # self.redis_client.delete("scraped_urls")
            except:
                pass
    
    def get_stats(self) -> dict:
        """Get deduplication statistics."""
        stats = {
            'strategy': self.strategy,
            'local_cache_size': len(self.url_cache),
            'bloom_filter_active': self.bloom_filter is not None,
            'redis_active': self.redis_client is not None,
            'opensearch_active': self.opensearch_client is not None
        }
        
        if self.redis_client:
            try:
                stats['redis_cache_size'] = self.redis_client.scard("scraped_urls")
            except:
                stats['redis_cache_size'] = 0
        
        return stats
    
    def save_state(self):
        """Save current state to disk."""
        if self.bloom_filter:
            self.bloom_filter.save_to_file("url_bloom_filter.json")
        
        # Save local cache
        cache_file = "url_cache.json"
        with open(cache_file, 'w') as f:
            json.dump(list(self.url_cache), f)
        
        print("💾 Deduplicator state saved")


# Example usage and integration
class ScraperWithDeduplication:
    """Example scraper integration with smart deduplication."""
    
    def __init__(self, deduplication_strategy: str = "bloom_and_db"):
        """Initialize scraper with deduplication."""
        self.deduplicator = SmartDeduplicator(strategy=deduplication_strategy)
        self.deduplicator.load_existing_urls()
    
    def scrape_urls(self, urls: List[str]) -> List[dict]:
        """Scrape URLs with deduplication."""
        # Filter out already scraped URLs
        new_urls = self.deduplicator.filter_new_urls(urls)
        
        if not new_urls:
            print("ℹ️ No new URLs to scrape")
            return []
        
        print(f"🕷️ Scraping {len(new_urls)} new URLs...")
        
        results = []
        for url in new_urls:
            # Simulate scraping
            result = self._scrape_single_url(url)
            if result:
                results.append(result)
                # Mark as successfully scraped
                self.deduplicator.mark_url_scraped(url)
        
        return results
    
    def _scrape_single_url(self, url: str) -> Optional[dict]:
        """Simulate scraping a single URL."""
        # This would be replaced with actual scraping logic
        return {
            'url': url,
            'content': f"Content from {url}",
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def cleanup_and_save(self):
        """Cleanup and save deduplicator state."""
        self.deduplicator.cleanup_old_entries()
        self.deduplicator.save_state()


def main():
    """Example usage of smart deduplication."""
    # Initialize deduplicator
    deduplicator = SmartDeduplicator(strategy="bloom_and_db")
    deduplicator.load_existing_urls()
    
    # Example URLs
    test_urls = [
        "http://example1.onion/page1",
        "http://example2.onion/page2",
        "http://example1.onion/page1",  # Duplicate
        "http://example3.onion/page3"
    ]
    
    # Filter new URLs
    new_urls = deduplicator.filter_new_urls(test_urls)
    print(f"New URLs to scrape: {new_urls}")
    
    # Get stats
    stats = deduplicator.get_stats()
    print(f"Deduplication stats: {stats}")
    
    # Save state
    deduplicator.save_state()


if __name__ == "__main__":
    main()
