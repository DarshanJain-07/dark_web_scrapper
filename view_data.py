#!/usr/bin/env python3
"""
Simple script to view scraped data from OpenSearch
"""
import requests
import json
from urllib3.exceptions import InsecureRequestWarning
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(InsecureRequestWarning)

# OpenSearch configuration
OPENSEARCH_URL = "https://localhost:9200"
INDEX_NAME = "darkweb-content"
USERNAME = "scraper_user"
PASSWORD = "uiyr83q8yuah879256755^^%$%yjhuir6544323***"

def get_document_count():
    """Get total number of documents in the index"""
    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_count"
    response = requests.get(url, auth=(USERNAME, PASSWORD), verify=False)
    if response.status_code == 200:
        return response.json()['count']
    return 0

def get_all_urls():
    """Get all URLs that have been scraped"""
    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"
    params = {
        "size": 100,
        "_source": "url,timestamp"
    }
    response = requests.get(url, auth=(USERNAME, PASSWORD), verify=False, params=params)
    if response.status_code == 200:
        hits = response.json()['hits']['hits']
        return [(hit['_source']['url'], hit['_source']['timestamp']) for hit in hits]
    return []

def search_content(query):
    """Search for specific content in the scraped data"""
    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"
    search_body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["text_content", "html_content"]
            }
        },
        "_source": ["url", "text_content", "timestamp"],
        "size": 10
    }
    response = requests.post(url, auth=(USERNAME, PASSWORD), verify=False, json=search_body)
    if response.status_code == 200:
        return response.json()['hits']['hits']
    return []

def get_latest_documents(count=5):
    """Get the latest scraped documents"""
    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"
    search_body = {
        "sort": [{"timestamp": {"order": "desc"}}],
        "_source": ["url", "text_content", "timestamp"],
        "size": count
    }
    response = requests.post(url, auth=(USERNAME, PASSWORD), verify=False, json=search_body)
    if response.status_code == 200:
        return response.json()['hits']['hits']
    return []

def get_full_document(doc_id):
    """Get full document by ID"""
    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_doc/{doc_id}"
    response = requests.get(url, auth=(USERNAME, PASSWORD), verify=False)
    if response.status_code == 200:
        return response.json()['_source']
    return None

def export_to_json(filename="scraped_data.json"):
    """Export all data to JSON file"""
    url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"
    search_body = {
        "size": 1000,
        "sort": [{"timestamp": {"order": "desc"}}]
    }
    response = requests.post(url, auth=(USERNAME, PASSWORD), verify=False, json=search_body)
    if response.status_code == 200:
        data = response.json()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    return False

def main():
    print("🕷️  Dark Web Scraper Data Viewer")
    print("=" * 50)

    # Get document count
    count = get_document_count()
    print(f"📊 Total documents scraped: {count}")
    print()

    while True:
        print("\nChoose an option:")
        print("1. View all URLs")
        print("2. View latest documents with content")
        print("3. Search content")
        print("4. View full document")
        print("5. Export all data to JSON")
        print("6. Exit")

        choice = input("\nEnter your choice (1-6): ").strip()

        if choice == "1":
            print("\n🔗 All scraped URLs:")
            urls = get_all_urls()
            for i, (url, timestamp) in enumerate(urls, 1):
                print(f"{i:2d}. {url}")
                print(f"    ⏰ {timestamp}")

        elif choice == "2":
            count_input = input("How many latest documents to show? (default 3): ").strip()
            count_to_show = int(count_input) if count_input.isdigit() else 3

            print(f"\n📰 Latest {count_to_show} documents:")
            latest = get_latest_documents(count_to_show)
            for i, doc in enumerate(latest, 1):
                source = doc['_source']
                print(f"\n{i}. {source['url']}")
                print(f"   ⏰ {source['timestamp']}")
                print(f"   📄 Content:")
                text = source.get('text_content', '')
                # Show first 500 characters
                if len(text) > 500:
                    print(f"   {text[:500]}...")
                    print(f"   [Content truncated - {len(text)} total characters]")
                else:
                    print(f"   {text}")
                print("-" * 80)

        elif choice == "3":
            query = input("Enter search term: ").strip()
            if query:
                print(f"\n🔍 Search results for '{query}':")
                results = search_content(query)
                for i, doc in enumerate(results, 1):
                    source = doc['_source']
                    print(f"\n{i}. {source['url']}")
                    print(f"   ⏰ {source['timestamp']}")
                    text = source.get('text_content', '')[:300]
                    print(f"   📄 {text}...")

        elif choice == "4":
            urls = get_all_urls()
            print("\nAvailable documents:")
            for i, (url, timestamp) in enumerate(urls, 1):
                print(f"{i:2d}. {url}")

            try:
                doc_num = int(input("Enter document number to view: ")) - 1
                if 0 <= doc_num < len(urls):
                    # Get the document ID from search results
                    url_to_find = urls[doc_num][0]
                    search_body = {"query": {"term": {"url.keyword": url_to_find}}}
                    search_url = f"{OPENSEARCH_URL}/{INDEX_NAME}/_search"
                    response = requests.post(search_url, auth=(USERNAME, PASSWORD), verify=False, json=search_body)
                    if response.status_code == 200:
                        hits = response.json()['hits']['hits']
                        if hits:
                            source = hits[0]['_source']
                            print(f"\n📄 Full content for: {source['url']}")
                            print(f"⏰ Timestamp: {source['timestamp']}")
                            print("=" * 80)
                            print(source.get('text_content', 'No text content available'))
                            print("=" * 80)
                else:
                    print("Invalid document number")
            except ValueError:
                print("Please enter a valid number")

        elif choice == "5":
            filename = input("Enter filename (default: scraped_data.json): ").strip()
            if not filename:
                filename = "scraped_data.json"

            print("Exporting data...")
            if export_to_json(filename):
                print(f"✅ Data exported to {filename}")
            else:
                print("❌ Failed to export data")

        elif choice == "6":
            print("Goodbye! 👋")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
