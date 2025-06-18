#!/usr/bin/env python3
"""
Database cleanup script for removing duplicates from Dark Web Scraper data.

This script provides comprehensive deduplication strategies:
1. URL-based deduplication (keep latest)
2. Content-based deduplication (identical content)
3. Smart deduplication (similar content)
4. Batch processing for large datasets
"""

import os
import sys
import hashlib
import argparse
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple
import json
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk, scan
from dotenv import load_dotenv
import difflib

# Load environment variables
load_dotenv()

class DuplicateCleanup:
    """Comprehensive duplicate cleanup for scraped data."""
    
    def __init__(self, dry_run: bool = True):
        """Initialize cleanup with OpenSearch connection."""
        self.client = self._get_opensearch_client()
        self.index_name = os.getenv("OPENSEARCH_INDEX", "darkweb-content")
        self.dry_run = dry_run
        self.stats = {
            'processed': 0,
            'url_duplicates_removed': 0,
            'content_duplicates_removed': 0,
            'total_removed': 0,
            'errors': 0
        }
    
    def _get_opensearch_client(self) -> OpenSearch:
        """Create OpenSearch client."""
        # Try both environment variable naming conventions
        username = os.getenv('OPENSEARCH_SCRAPER_USER') or os.getenv('OPENSEARCH_USER')
        password = os.getenv('OPENSEARCH_SCRAPER_PASSWORD') or os.getenv('OPENSEARCH_PASSWORD')

        return OpenSearch(
            hosts=[f"https://{os.getenv('OPENSEARCH_HOST', 'localhost')}:9200"],
            http_auth=(username, password),
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False,
            timeout=60
        )
    
    def get_all_documents(self) -> List[Dict]:
        """Retrieve all documents from the index."""
        print("📥 Retrieving all documents...")
        
        query = {
            "query": {"match_all": {}},
            "_source": ["url", "text_content", "html_content", "timestamp"],
            "sort": [{"timestamp": {"order": "desc"}}]
        }
        
        documents = []
        for doc in scan(self.client, query=query, index=self.index_name, scroll='5m'):
            documents.append({
                'id': doc['_id'],
                'url': doc['_source'].get('url', ''),
                'text_content': doc['_source'].get('text_content', ''),
                'html_content': doc['_source'].get('html_content', ''),
                'timestamp': doc['_source'].get('timestamp', ''),
                'source': doc['_source']
            })
        
        print(f"📊 Retrieved {len(documents)} documents")
        return documents
    
    def find_url_duplicates(self, documents: List[Dict]) -> Dict[str, List[Dict]]:
        """Find documents with duplicate URLs."""
        print("🔍 Finding URL duplicates...")
        
        url_groups = defaultdict(list)
        
        for doc in documents:
            url = doc['url']
            if url:  # Skip empty URLs
                url_groups[url].append(doc)
        
        # Filter to only groups with duplicates
        duplicates = {url: docs for url, docs in url_groups.items() if len(docs) > 1}
        
        total_duplicates = sum(len(docs) - 1 for docs in duplicates.values())
        print(f"📊 Found {len(duplicates)} URLs with duplicates ({total_duplicates} extra documents)")
        
        return duplicates
    
    def find_content_duplicates(self, documents: List[Dict]) -> Dict[str, List[Dict]]:
        """Find documents with identical content."""
        print("🔍 Finding content duplicates...")
        
        content_groups = defaultdict(list)
        
        for doc in documents:
            content = doc['text_content']
            if content and len(content.strip()) > 50:  # Skip very short content
                # Create hash of content
                content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                content_groups[content_hash].append(doc)
        
        # Filter to only groups with duplicates
        duplicates = {hash_val: docs for hash_val, docs in content_groups.items() if len(docs) > 1}
        
        total_duplicates = sum(len(docs) - 1 for docs in duplicates.values())
        print(f"📊 Found {len(duplicates)} content groups with duplicates ({total_duplicates} extra documents)")
        
        return duplicates
    
    def find_similar_content(self, documents: List[Dict], similarity_threshold: float = 0.95) -> Dict[str, List[Dict]]:
        """Find documents with very similar content."""
        print(f"🔍 Finding similar content (threshold: {similarity_threshold})...")
        
        # This is computationally expensive, so we'll sample for large datasets
        if len(documents) > 1000:
            print("⚠️ Large dataset detected, sampling for similarity analysis...")
            import random
            documents = random.sample(documents, 1000)
        
        similar_groups = []
        processed = set()
        
        for i, doc1 in enumerate(documents):
            if doc1['id'] in processed:
                continue
                
            content1 = doc1['text_content']
            if not content1 or len(content1.strip()) < 100:
                continue
            
            similar_docs = [doc1]
            processed.add(doc1['id'])
            
            for j, doc2 in enumerate(documents[i+1:], i+1):
                if doc2['id'] in processed:
                    continue
                    
                content2 = doc2['text_content']
                if not content2 or len(content2.strip()) < 100:
                    continue
                
                # Calculate similarity
                similarity = difflib.SequenceMatcher(None, content1, content2).ratio()
                
                if similarity >= similarity_threshold:
                    similar_docs.append(doc2)
                    processed.add(doc2['id'])
            
            if len(similar_docs) > 1:
                similar_groups.append(similar_docs)
        
        # Convert to dict format
        similar_dict = {f"group_{i}": docs for i, docs in enumerate(similar_groups)}
        
        total_similar = sum(len(docs) - 1 for docs in similar_groups)
        print(f"📊 Found {len(similar_groups)} similar content groups ({total_similar} extra documents)")
        
        return similar_dict
    
    def select_documents_to_keep(self, duplicate_groups: Dict[str, List[Dict]], strategy: str = "latest") -> Set[str]:
        """Select which documents to keep from duplicate groups."""
        to_remove = set()
        
        for group_key, docs in duplicate_groups.items():
            if len(docs) <= 1:
                continue
            
            if strategy == "latest":
                # Keep the document with the latest timestamp
                latest_doc = max(docs, key=lambda x: x['timestamp'])
                for doc in docs:
                    if doc['id'] != latest_doc['id']:
                        to_remove.add(doc['id'])
            
            elif strategy == "longest_content":
                # Keep the document with the longest content
                longest_doc = max(docs, key=lambda x: len(x['text_content']))
                for doc in docs:
                    if doc['id'] != longest_doc['id']:
                        to_remove.add(doc['id'])
            
            elif strategy == "first":
                # Keep the first document (oldest)
                first_doc = min(docs, key=lambda x: x['timestamp'])
                for doc in docs:
                    if doc['id'] != first_doc['id']:
                        to_remove.add(doc['id'])
        
        return to_remove
    
    def remove_documents(self, document_ids: Set[str]) -> bool:
        """Remove documents from OpenSearch."""
        if not document_ids:
            print("ℹ️ No documents to remove")
            return True
        
        if self.dry_run:
            print(f"🔍 DRY RUN: Would remove {len(document_ids)} documents")
            return True
        
        print(f"🗑️ Removing {len(document_ids)} documents...")
        
        # Prepare bulk delete operations
        actions = []
        for doc_id in document_ids:
            actions.append({
                "_op_type": "delete",
                "_index": self.index_name,
                "_id": doc_id
            })
        
        try:
            # Execute bulk delete
            success, failed = bulk(self.client, actions, chunk_size=100)
            
            if failed:
                print(f"⚠️ Failed to delete {len(failed)} documents")
                self.stats['errors'] += len(failed)
                return False
            
            print(f"✅ Successfully removed {success} documents")
            return True
            
        except Exception as e:
            print(f"❌ Error during bulk delete: {e}")
            self.stats['errors'] += len(document_ids)
            return False
    
    def cleanup_url_duplicates(self, documents: List[Dict], strategy: str = "latest") -> int:
        """Clean up URL-based duplicates."""
        print(f"\n🔗 Cleaning URL duplicates (strategy: {strategy})...")
        
        url_duplicates = self.find_url_duplicates(documents)
        to_remove = self.select_documents_to_keep(url_duplicates, strategy)
        
        if self.remove_documents(to_remove):
            self.stats['url_duplicates_removed'] = len(to_remove)
            return len(to_remove)
        
        return 0
    
    def cleanup_content_duplicates(self, documents: List[Dict], strategy: str = "latest") -> int:
        """Clean up content-based duplicates."""
        print(f"\n📄 Cleaning content duplicates (strategy: {strategy})...")
        
        content_duplicates = self.find_content_duplicates(documents)
        to_remove = self.select_documents_to_keep(content_duplicates, strategy)
        
        if self.remove_documents(to_remove):
            self.stats['content_duplicates_removed'] = len(to_remove)
            return len(to_remove)
        
        return 0
    
    def cleanup_similar_content(self, documents: List[Dict], similarity_threshold: float = 0.95, strategy: str = "latest") -> int:
        """Clean up similar content."""
        print(f"\n🔄 Cleaning similar content (threshold: {similarity_threshold}, strategy: {strategy})...")
        
        similar_content = self.find_similar_content(documents, similarity_threshold)
        to_remove = self.select_documents_to_keep(similar_content, strategy)
        
        if self.remove_documents(to_remove):
            return len(to_remove)
        
        return 0
    
    def run_cleanup(self, cleanup_types: List[str], strategy: str = "latest", similarity_threshold: float = 0.95) -> Dict:
        """Run comprehensive cleanup."""
        print("🚀 Starting database cleanup...")
        print(f"🔧 Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"📋 Cleanup types: {', '.join(cleanup_types)}")
        print(f"📊 Strategy: {strategy}")
        print("=" * 60)
        
        # Get all documents
        documents = self.get_all_documents()
        self.stats['processed'] = len(documents)
        
        total_removed = 0
        
        # Run selected cleanup types
        if "url" in cleanup_types:
            removed = self.cleanup_url_duplicates(documents, strategy)
            total_removed += removed
        
        if "content" in cleanup_types:
            removed = self.cleanup_content_duplicates(documents, strategy)
            total_removed += removed
        
        if "similar" in cleanup_types:
            removed = self.cleanup_similar_content(documents, similarity_threshold, strategy)
            total_removed += removed
        
        self.stats['total_removed'] = total_removed
        
        # Print final stats
        print("\n📊 CLEANUP SUMMARY")
        print("=" * 60)
        print(f"📈 Documents Processed: {self.stats['processed']:,}")
        print(f"🔗 URL Duplicates Removed: {self.stats['url_duplicates_removed']:,}")
        print(f"📄 Content Duplicates Removed: {self.stats['content_duplicates_removed']:,}")
        print(f"🗑️ Total Removed: {self.stats['total_removed']:,}")
        print(f"❌ Errors: {self.stats['errors']:,}")
        
        if self.dry_run:
            print("\n⚠️ This was a DRY RUN - no documents were actually removed")
            print("   Run with --live to perform actual cleanup")
        
        return self.stats


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description="Clean up duplicate documents from Dark Web Scraper database")
    
    parser.add_argument("--live", action="store_true", help="Perform actual cleanup (default is dry run)")
    parser.add_argument("--strategy", choices=["latest", "longest_content", "first"], default="latest",
                       help="Strategy for selecting documents to keep")
    parser.add_argument("--types", nargs="+", choices=["url", "content", "similar"], default=["url", "content"],
                       help="Types of cleanup to perform")
    parser.add_argument("--similarity", type=float, default=0.95,
                       help="Similarity threshold for similar content cleanup (0.0-1.0)")
    
    args = parser.parse_args()
    
    try:
        cleanup = DuplicateCleanup(dry_run=not args.live)
        results = cleanup.run_cleanup(
            cleanup_types=args.types,
            strategy=args.strategy,
            similarity_threshold=args.similarity
        )
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f"cleanup_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
