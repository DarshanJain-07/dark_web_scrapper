#!/usr/bin/env python3
"""
Test script for the Dark Web Scraper API.

This script tests all API endpoints to ensure they're working correctly.
Run this after starting the API service with docker compose.
"""

import requests
import json
import time
import sys
from typing import Dict, Any


class APITester:
    """Test class for the Dark Web Scraper API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the API tester."""
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 30
    
    def test_root(self) -> bool:
        """Test the root endpoint."""
        print("Testing root endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/")
            response.raise_for_status()
            data = response.json()
            
            assert "message" in data
            assert "version" in data
            print("✅ Root endpoint working")
            return True
        except Exception as e:
            print(f"❌ Root endpoint failed: {e}")
            return False
    
    def test_health(self) -> bool:
        """Test the health check endpoint."""
        print("Testing health endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            
            assert "status" in data
            assert "timestamp" in data
            assert "opensearch_connected" in data
            
            if data["status"] == "healthy":
                print("✅ Health check passed - API is healthy")
                return True
            else:
                print(f"⚠️ Health check shows unhealthy status: {data.get('error', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    def test_stats(self) -> bool:
        """Test the statistics endpoint."""
        print("Testing stats endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/stats")
            response.raise_for_status()
            data = response.json()
            
            assert "total_documents" in data
            assert "unique_urls" in data
            
            print(f"✅ Stats endpoint working - {data['total_documents']} documents, {data['unique_urls']} unique URLs")
            return True
        except Exception as e:
            print(f"❌ Stats endpoint failed: {e}")
            return False
    
    def test_documents(self) -> bool:
        """Test the documents endpoint."""
        print("Testing documents endpoint...")
        try:
            # Test basic documents endpoint
            response = self.session.get(f"{self.base_url}/documents")
            response.raise_for_status()
            data = response.json()
            
            assert "documents" in data
            assert "total" in data
            assert "page" in data
            assert "size" in data
            assert "total_pages" in data
            
            print(f"✅ Documents endpoint working - {len(data['documents'])} documents returned")
            
            # Test with parameters
            response = self.session.get(f"{self.base_url}/documents?page=1&size=5&sort_field=timestamp&sort_order=desc")
            response.raise_for_status()
            data = response.json()
            
            assert len(data["documents"]) <= 5
            print("✅ Documents endpoint with parameters working")
            return True
        except Exception as e:
            print(f"❌ Documents endpoint failed: {e}")
            return False
    
    def test_search(self) -> bool:
        """Test the search endpoint."""
        print("Testing search endpoint...")
        try:
            # Test search with a common term
            response = self.session.get(f"{self.base_url}/search?q=http")
            response.raise_for_status()
            data = response.json()
            
            assert "documents" in data
            assert "total" in data
            assert "took" in data
            
            print(f"✅ Search endpoint working - found {data['total']} results for 'http'")
            
            # Test search with pagination
            response = self.session.get(f"{self.base_url}/search?q=onion&page=1&size=3")
            response.raise_for_status()
            data = response.json()
            
            assert len(data["documents"]) <= 3
            print("✅ Search endpoint with pagination working")
            return True
        except Exception as e:
            print(f"❌ Search endpoint failed: {e}")
            return False
    
    def test_urls(self) -> bool:
        """Test the URLs endpoint."""
        print("Testing URLs endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/urls")
            response.raise_for_status()
            data = response.json()
            
            assert "urls" in data
            assert "total" in data
            assert "page" in data
            assert "size" in data
            
            print(f"✅ URLs endpoint working - {len(data['urls'])} URLs returned")
            return True
        except Exception as e:
            print(f"❌ URLs endpoint failed: {e}")
            return False
    
    def test_document_by_url(self) -> bool:
        """Test getting a specific document by URL."""
        print("Testing document by URL endpoint...")
        try:
            # First get a URL from the URLs endpoint
            response = self.session.get(f"{self.base_url}/urls?size=1")
            response.raise_for_status()
            urls_data = response.json()
            
            if not urls_data["urls"]:
                print("⚠️ No URLs available to test document endpoint")
                return True
            
            test_url = urls_data["urls"][0]
            
            # Now test getting the document
            response = self.session.get(f"{self.base_url}/document", params={"url": test_url})
            response.raise_for_status()
            data = response.json()
            
            assert "document" in data
            assert "found" in data
            
            if data["found"]:
                print(f"✅ Document by URL endpoint working - found document for {test_url}")
            else:
                print(f"⚠️ Document not found for URL {test_url}")
            
            return True
        except Exception as e:
            print(f"❌ Document by URL endpoint failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all API tests."""
        print(f"🚀 Starting API tests for {self.base_url}")
        print("=" * 50)
        
        tests = [
            self.test_root,
            self.test_health,
            self.test_stats,
            self.test_documents,
            self.test_search,
            self.test_urls,
            self.test_document_by_url
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            try:
                if test():
                    passed += 1
                print()  # Add spacing between tests
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {e}")
                print()
        
        print("=" * 50)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! API is working correctly.")
            return True
        else:
            print("⚠️ Some tests failed. Check the API configuration and OpenSearch connection.")
            return False


def main():
    """Main function to run the tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the Dark Web Scraper API")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--wait", type=int, default=0, help="Wait time before starting tests (seconds)")
    
    args = parser.parse_args()
    
    if args.wait > 0:
        print(f"⏳ Waiting {args.wait} seconds for services to start...")
        time.sleep(args.wait)
    
    tester = APITester(args.url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
