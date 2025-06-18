#!/usr/bin/env python3
"""
Example usage of the Dark Web Scraper API.

This script demonstrates how to use the API to retrieve and search scraped data.
"""

import requests
import json
from datetime import datetime
from typing import List, Dict, Any


class DarkWebAPI:
    """Client for the Dark Web Scraper API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the API client."""
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30
    
    def get_health(self) -> Dict[str, Any]:
        """Get API health status."""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get data statistics."""
        response = self.session.get(f"{self.base_url}/stats")
        response.raise_for_status()
        return response.json()
    
    def get_documents(self, page: int = 1, size: int = 20, include_html: bool = False) -> Dict[str, Any]:
        """Get all documents with pagination."""
        params = {
            "page": page,
            "size": size,
            "include_html": include_html
        }
        response = self.session.get(f"{self.base_url}/documents", params=params)
        response.raise_for_status()
        return response.json()
    
    def search_documents(self, query: str, page: int = 1, size: int = 20, include_html: bool = False) -> Dict[str, Any]:
        """Search through documents."""
        params = {
            "q": query,
            "page": page,
            "size": size,
            "include_html": include_html
        }
        response = self.session.get(f"{self.base_url}/search", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_document_by_url(self, url: str, include_html: bool = False) -> Dict[str, Any]:
        """Get a specific document by URL."""
        params = {
            "url": url,
            "include_html": include_html
        }
        response = self.session.get(f"{self.base_url}/document", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_urls(self, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """Get list of all scraped URLs."""
        params = {
            "page": page,
            "size": size
        }
        response = self.session.get(f"{self.base_url}/urls", params=params)
        response.raise_for_status()
        return response.json()


def print_stats(api: DarkWebAPI):
    """Print data statistics."""
    print("📊 Data Statistics")
    print("=" * 40)
    
    try:
        stats = api.get_stats()
        print(f"Total Documents: {stats['total_documents']:,}")
        print(f"Unique URLs: {stats['unique_urls']:,}")
        print(f"Index Size: {stats.get('index_size', 'Unknown')}")
        
        if stats.get('latest_scrape'):
            latest = datetime.fromisoformat(stats['latest_scrape'].replace('Z', '+00:00'))
            print(f"Latest Scrape: {latest.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        if stats.get('oldest_scrape'):
            oldest = datetime.fromisoformat(stats['oldest_scrape'].replace('Z', '+00:00'))
            print(f"Oldest Scrape: {oldest.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
    
    print()


def print_recent_documents(api: DarkWebAPI, count: int = 5):
    """Print recent documents."""
    print(f"📄 Recent Documents (Latest {count})")
    print("=" * 40)
    
    try:
        result = api.get_documents(page=1, size=count)
        
        for i, doc in enumerate(result['documents'], 1):
            timestamp = datetime.fromisoformat(doc['timestamp'].replace('Z', '+00:00'))
            print(f"{i}. {doc['url']}")
            print(f"   Scraped: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"   Content: {doc['text_content'][:100]}...")
            print()
        
        print(f"Total documents available: {result['total']:,}")
        
    except Exception as e:
        print(f"❌ Failed to get documents: {e}")
    
    print()


def search_example(api: DarkWebAPI, query: str):
    """Demonstrate search functionality."""
    print(f"🔍 Search Results for '{query}'")
    print("=" * 40)
    
    try:
        result = api.search_documents(query, size=5)
        
        if result['total'] == 0:
            print("No results found.")
        else:
            print(f"Found {result['total']} results (showing first {len(result['documents'])})")
            print(f"Search took {result['took']}ms")
            print()
            
            for i, doc in enumerate(result['documents'], 1):
                timestamp = datetime.fromisoformat(doc['timestamp'].replace('Z', '+00:00'))
                score = doc.get('score', 0)
                print(f"{i}. {doc['url']} (Score: {score:.2f})")
                print(f"   Scraped: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                print(f"   Content: {doc['text_content'][:150]}...")
                print()
        
    except Exception as e:
        print(f"❌ Search failed: {e}")
    
    print()


def list_urls_example(api: DarkWebAPI, count: int = 10):
    """List scraped URLs."""
    print(f"🔗 Scraped URLs (First {count})")
    print("=" * 40)
    
    try:
        result = api.get_urls(size=count)
        
        for i, url in enumerate(result['urls'], 1):
            print(f"{i}. {url}")
        
        print(f"\nTotal URLs: {result['total']:,}")
        
    except Exception as e:
        print(f"❌ Failed to get URLs: {e}")
    
    print()


def main():
    """Main example function."""
    print("🕸️ Dark Web Scraper API Examples")
    print("=" * 50)
    
    # Initialize API client
    api = DarkWebAPI()
    
    # Check API health
    try:
        health = api.get_health()
        if health['status'] == 'healthy':
            print("✅ API is healthy and ready")
        else:
            print(f"⚠️ API health check failed: {health.get('error', 'Unknown error')}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("Make sure the API is running with: docker compose up -d")
        return
    
    print()
    
    # Show statistics
    print_stats(api)
    
    # Show recent documents
    print_recent_documents(api)
    
    # Search examples
    search_terms = ["bitcoin", "marketplace", "forum", "onion"]
    for term in search_terms:
        search_example(api, term)
    
    # List URLs
    list_urls_example(api)
    
    print("🎉 Examples completed!")
    print("\nTry these API endpoints in your browser:")
    print("- http://localhost:8000/docs (Interactive API documentation)")
    print("- http://localhost:8000/health (Health check)")
    print("- http://localhost:8000/stats (Data statistics)")


if __name__ == "__main__":
    main()
