#!/usr/bin/env python3
"""
Duplicate data analyzer for the Dark Web Scraper.

This script analyzes the current data to identify duplicate patterns
and provides insights for deduplication strategies.
"""

import os
import sys
import hashlib
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Tuple, Set
import json
from opensearchpy import OpenSearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DuplicateAnalyzer:
    """Analyzer for identifying duplicate patterns in scraped data."""
    
    def __init__(self):
        """Initialize the analyzer with OpenSearch connection."""
        self.client = self._get_opensearch_client()
        self.index_name = os.getenv("OPENSEARCH_INDEX", "darkweb-content")
    
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
            timeout=30
        )
    
    def analyze_url_duplicates(self) -> Dict:
        """Analyze URL-based duplicates."""
        print("🔍 Analyzing URL duplicates...")
        
        # Get all documents with URLs
        query = {
            "size": 10000,  # Adjust based on your data size
            "_source": ["url", "timestamp"],
            "sort": [{"timestamp": {"order": "desc"}}]
        }
        
        response = self.client.search(index=self.index_name, body=query)
        documents = response['hits']['hits']
        
        # Count URL occurrences
        url_counts = Counter()
        url_timestamps = defaultdict(list)
        
        for doc in documents:
            url = doc['_source'].get('url')
            timestamp = doc['_source'].get('timestamp')
            if url:  # Only process documents with valid URLs
                url_counts[url] += 1
                url_timestamps[url].append(timestamp)
        
        # Find duplicates
        duplicates = {url: count for url, count in url_counts.items() if count > 1}
        
        return {
            'total_documents': len(documents),
            'unique_urls': len(url_counts),
            'duplicate_urls': len(duplicates),
            'total_duplicates': sum(duplicates.values()) - len(duplicates),
            'duplicate_details': duplicates,
            'url_timestamps': dict(url_timestamps)
        }
    
    def analyze_content_duplicates(self) -> Dict:
        """Analyze content-based duplicates using content hashing."""
        print("🔍 Analyzing content duplicates...")
        
        query = {
            "size": 10000,
            "_source": ["url", "text_content", "timestamp"],
            "sort": [{"timestamp": {"order": "desc"}}]
        }
        
        response = self.client.search(index=self.index_name, body=query)
        documents = response['hits']['hits']
        
        # Create content hashes
        content_hashes = defaultdict(list)
        
        for doc in documents:
            content = doc['_source'].get('text_content', '')
            url = doc['_source'].get('url')
            timestamp = doc['_source'].get('timestamp')
            if content and url:  # Only process documents with valid content and URL
                # Create hash of content
                content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
                content_hashes[content_hash].append({
                    'url': url,
                    'timestamp': timestamp,
                    'content_length': len(content)
                })
        
        # Find content duplicates
        content_duplicates = {
            hash_val: docs for hash_val, docs in content_hashes.items() 
            if len(docs) > 1
        }
        
        return {
            'total_content_hashes': len(content_hashes),
            'duplicate_content_groups': len(content_duplicates),
            'total_content_duplicates': sum(len(docs) - 1 for docs in content_duplicates.values()),
            'duplicate_details': content_duplicates
        }
    
    def analyze_temporal_patterns(self) -> Dict:
        """Analyze when duplicates occur (temporal patterns)."""
        print("🔍 Analyzing temporal duplicate patterns...")
        
        query = {
            "size": 10000,
            "_source": ["url", "timestamp"],
            "sort": [{"timestamp": {"order": "asc"}}]
        }
        
        response = self.client.search(index=self.index_name, body=query)
        documents = response['hits']['hits']
        
        # Group by URL and analyze timestamps
        url_timeline = defaultdict(list)
        
        for doc in documents:
            url = doc['_source'].get('url')
            timestamp = doc['_source'].get('timestamp')
            if url and timestamp:  # Only process documents with valid URL and timestamp
                url_timeline[url].append(timestamp)
        
        # Analyze patterns
        patterns = {
            'same_day_duplicates': 0,
            'same_hour_duplicates': 0,
            'rapid_duplicates': 0,  # Within 5 minutes
            'url_frequency': {}
        }
        
        for url, timestamps in url_timeline.items():
            if len(timestamps) > 1:
                patterns['url_frequency'][url] = len(timestamps)
                
                # Convert to datetime objects for comparison
                dt_timestamps = []
                for ts in timestamps:
                    try:
                        if isinstance(ts, str):
                            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        else:
                            dt = datetime.fromtimestamp(ts / 1000)
                        dt_timestamps.append(dt)
                    except:
                        continue
                
                dt_timestamps.sort()
                
                # Check for same day duplicates
                dates = set(dt.date() for dt in dt_timestamps)
                if len(dates) < len(dt_timestamps):
                    patterns['same_day_duplicates'] += 1
                
                # Check for same hour duplicates
                hours = set((dt.date(), dt.hour) for dt in dt_timestamps)
                if len(hours) < len(dt_timestamps):
                    patterns['same_hour_duplicates'] += 1
                
                # Check for rapid duplicates (within 5 minutes)
                for i in range(1, len(dt_timestamps)):
                    time_diff = dt_timestamps[i] - dt_timestamps[i-1]
                    if time_diff.total_seconds() < 300:  # 5 minutes
                        patterns['rapid_duplicates'] += 1
                        break
        
        return patterns
    
    def get_cleanup_recommendations(self, url_analysis: Dict, content_analysis: Dict, temporal_analysis: Dict) -> List[str]:
        """Generate cleanup recommendations based on analysis."""
        recommendations = []
        
        # URL-based recommendations
        if url_analysis['duplicate_urls'] > 0:
            recommendations.append(
                f"🔗 Found {url_analysis['duplicate_urls']} URLs with duplicates "
                f"({url_analysis['total_duplicates']} extra documents). "
                "Recommend keeping only the latest version of each URL."
            )
        
        # Content-based recommendations
        if content_analysis['duplicate_content_groups'] > 0:
            recommendations.append(
                f"📄 Found {content_analysis['duplicate_content_groups']} groups of identical content "
                f"({content_analysis['total_content_duplicates']} duplicates). "
                "Consider removing content duplicates even if URLs differ."
            )
        
        # Temporal recommendations
        if temporal_analysis['rapid_duplicates'] > 0:
            recommendations.append(
                f"⚡ Found {temporal_analysis['rapid_duplicates']} rapid duplicates (within 5 minutes). "
                "Consider adding delay between scraping same URLs."
            )
        
        if temporal_analysis['same_hour_duplicates'] > 0:
            recommendations.append(
                f"🕐 Found {temporal_analysis['same_hour_duplicates']} URLs scraped multiple times in same hour. "
                "Consider implementing hourly deduplication checks."
            )
        
        # Efficiency recommendations
        total_docs = url_analysis['total_documents']
        unique_urls = url_analysis['unique_urls']
        efficiency = (unique_urls / total_docs) * 100 if total_docs > 0 else 0
        
        recommendations.append(
            f"📊 Current efficiency: {efficiency:.1f}% ({unique_urls}/{total_docs} unique). "
            f"Potential space savings: {total_docs - unique_urls} documents."
        )
        
        return recommendations
    
    def run_full_analysis(self) -> Dict:
        """Run complete duplicate analysis."""
        print("🚀 Starting comprehensive duplicate analysis...")
        print("=" * 60)
        
        # Run all analyses
        url_analysis = self.analyze_url_duplicates()
        content_analysis = self.analyze_content_duplicates()
        temporal_analysis = self.analyze_temporal_patterns()
        
        # Generate recommendations
        recommendations = self.get_cleanup_recommendations(
            url_analysis, content_analysis, temporal_analysis
        )

        # Filter out any None recommendations
        recommendations = [rec for rec in recommendations if rec is not None]
        
        # Compile results
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'url_analysis': url_analysis,
            'content_analysis': content_analysis,
            'temporal_analysis': temporal_analysis,
            'recommendations': recommendations
        }
        
        return results
    
    def print_analysis_report(self, results: Dict):
        """Print a formatted analysis report."""
        print("\n📊 DUPLICATE ANALYSIS REPORT")
        print("=" * 60)
        
        url_analysis = results['url_analysis']
        content_analysis = results['content_analysis']
        temporal_analysis = results['temporal_analysis']
        
        print(f"📈 Overall Statistics:")
        print(f"   Total Documents: {url_analysis['total_documents']:,}")
        print(f"   Unique URLs: {url_analysis['unique_urls']:,}")
        print(f"   Duplicate URLs: {url_analysis['duplicate_urls']:,}")
        print(f"   Total URL Duplicates: {url_analysis['total_duplicates']:,}")
        
        print(f"\n📄 Content Analysis:")
        print(f"   Content Groups: {content_analysis['total_content_hashes']:,}")
        print(f"   Duplicate Content Groups: {content_analysis['duplicate_content_groups']:,}")
        print(f"   Total Content Duplicates: {content_analysis['total_content_duplicates']:,}")
        
        print(f"\n⏰ Temporal Patterns:")
        print(f"   Same Day Duplicates: {temporal_analysis['same_day_duplicates']:,}")
        print(f"   Same Hour Duplicates: {temporal_analysis['same_hour_duplicates']:,}")
        print(f"   Rapid Duplicates (5min): {temporal_analysis['rapid_duplicates']:,}")
        
        print(f"\n💡 Recommendations:")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"   {i}. {rec}")
        
        print(f"\n🔝 Top Duplicate URLs:")
        duplicate_details = url_analysis['duplicate_details']
        sorted_duplicates = sorted(duplicate_details.items(), key=lambda x: x[1], reverse=True)
        
        for url, count in sorted_duplicates[:10]:  # Top 10
            print(f"   {count}x: {url}")
        
        print("\n" + "=" * 60)


def main():
    """Main function to run duplicate analysis."""
    try:
        analyzer = DuplicateAnalyzer()
        results = analyzer.run_full_analysis()
        analyzer.print_analysis_report(results)
        
        # Save results to file
        output_file = f"duplicate_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
