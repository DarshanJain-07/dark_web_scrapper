# Dark Web Scraper Deduplication System

A comprehensive deduplication solution for the Dark Web Scraper that prevents and removes duplicate data efficiently.

## 🎯 Features

### 1. **Smart Prevention**
- **Bloom Filter**: Fast URL checking with minimal memory usage
- **Redis Cache**: Distributed URL tracking for multiple scrapers
- **Database Integration**: Accurate duplicate detection
- **Configurable Strategies**: Choose between speed and accuracy

### 2. **Comprehensive Cleanup**
- **URL Deduplication**: Remove documents with identical URLs
- **Content Deduplication**: Remove documents with identical content
- **Similar Content**: Remove documents with highly similar content
- **Batch Processing**: Handle large datasets efficiently

### 3. **Automated Scheduling**
- **Cron-based Service**: Automated cleanup on schedule
- **Threshold Monitoring**: Trigger cleanup when duplicates exceed limits
- **Email Notifications**: Get notified of cleanup results
- **Configurable Schedules**: Daily, weekly, monthly cleanup options

### 4. **API Integration**
- **Analysis Endpoints**: Get duplicate statistics via API
- **Manual Cleanup**: Trigger cleanup through API calls
- **Real-time Monitoring**: Monitor deduplication status

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install deduplication requirements
uv add schedule redis difflib2

# Or install from requirements file
uv add -r deduplication/requirements.txt
```

### 2. Run Duplicate Analysis

```bash
# Analyze current duplicate patterns
uv run python deduplication/duplicate_analyzer.py
```

### 3. Clean Up Duplicates

```bash
# Dry run (safe - no actual deletion)
uv run python deduplication/cleanup_duplicates.py --types url content

# Live cleanup (actual deletion)
uv run python deduplication/cleanup_duplicates.py --live --types url content --strategy latest
```

### 4. Start Automated Service

```bash
# Run cleanup service
uv run python deduplication/cron_cleanup_service.py

# Run once and exit
uv run python deduplication/cron_cleanup_service.py --once --type full
```

## 📊 Usage Examples

### Analyze Duplicates

```bash
# Get comprehensive duplicate analysis
curl http://localhost:8000/duplicates/analyze
```

### Manual Cleanup via API

```bash
# Trigger cleanup via API (dry run)
curl -X POST http://localhost:8000/duplicates/cleanup \
  -H "Content-Type: application/json" \
  -d '{
    "cleanup_types": ["url", "content"],
    "strategy": "latest",
    "dry_run": true
  }'
```

### Smart Deduplication in Scraper

```python
from deduplication.smart_deduplicator import SmartDeduplicator

# Initialize deduplicator
deduplicator = SmartDeduplicator(strategy="bloom_and_db")
deduplicator.load_existing_urls()

# Filter URLs before scraping
urls_to_scrape = ["http://example1.onion", "http://example2.onion"]
new_urls = deduplicator.filter_new_urls(urls_to_scrape)

# Scrape only new URLs
for url in new_urls:
    # Scrape the URL
    result = scrape_url(url)
    
    # Mark as scraped
    deduplicator.mark_url_scraped(url)
```

## ⚙️ Configuration

### Cleanup Service Configuration

Edit `deduplication/cleanup_config.json`:

```json
{
  "schedules": {
    "daily_light_cleanup": "02:00",
    "weekly_full_cleanup": "sunday 03:00",
    "monthly_deep_cleanup": "1 04:00"
  },
  "cleanup_settings": {
    "url_duplicates": true,
    "content_duplicates": true,
    "similar_content": false,
    "similarity_threshold": 0.95,
    "strategy": "latest",
    "dry_run": false
  },
  "thresholds": {
    "max_duplicates_percent": 20,
    "max_index_size_gb": 10,
    "min_cleanup_interval_hours": 6
  }
}
```

### Deduplication Strategies

- **`latest`**: Keep the most recently scraped version
- **`longest_content`**: Keep the version with most content
- **`first`**: Keep the first scraped version

### Cleanup Types

- **`url`**: Remove URL duplicates (same URL, different timestamps)
- **`content`**: Remove content duplicates (identical content, different URLs)
- **`similar`**: Remove similar content (configurable similarity threshold)

## 📈 Performance Impact

### Before Deduplication
- **34 documents** in database
- **0 unique URLs** (100% duplicates!)
- **27.5 MB** index size
- **Poor search performance** due to duplicates

### After Deduplication (Expected)
- **~10-15 documents** (estimated unique content)
- **~10-15 unique URLs**
- **~8-12 MB** index size
- **Improved search performance**
- **Faster scraping** (no re-scraping)

## 🔧 Advanced Features

### Bloom Filter Optimization

```python
# Configure Bloom filter for your dataset size
bloom = BloomFilter(capacity=1000000, error_rate=0.1)

# Save/load filter state
bloom.save_to_file("url_bloom_filter.json")
bloom = BloomFilter.load_from_file("url_bloom_filter.json")
```

### Redis Integration

```python
# Use Redis for distributed deduplication
deduplicator = SmartDeduplicator(
    strategy="redis_and_db",
    redis_url="redis://localhost:6379"
)
```

### Custom Similarity Threshold

```bash
# Adjust similarity threshold for content deduplication
python cleanup_duplicates.py --types similar --similarity 0.90
```

## 📊 Monitoring & Reporting

### Analysis Reports

The system generates detailed analysis reports:

```json
{
  "total_documents": 34,
  "unique_urls": 10,
  "duplicate_urls": 5,
  "total_duplicates": 24,
  "efficiency_percent": 29.4,
  "recommendations": [
    "Found 5 URLs with duplicates (24 extra documents)",
    "Current efficiency: 29.4% (10/34 unique)"
  ]
}
```

### Cleanup Results

```json
{
  "documents_processed": 34,
  "url_duplicates_removed": 20,
  "content_duplicates_removed": 4,
  "total_removed": 24,
  "errors": 0
}
```

## 🚨 Safety Features

### Dry Run Mode
- **Default behavior**: All operations are dry runs
- **Safe testing**: See what would be removed without actual deletion
- **Explicit confirmation**: Must use `--live` flag for actual cleanup

### Backup Recommendations
- **Database snapshots**: Take OpenSearch snapshots before cleanup
- **Export data**: Use the API to export important data
- **Gradual cleanup**: Start with small batches

### Error Handling
- **Graceful failures**: Continue processing even if some operations fail
- **Detailed logging**: All operations are logged with timestamps
- **Rollback capability**: Keep track of removed documents for potential recovery

## 🔄 Integration with Existing Scraper

### Update Scraper Code

```python
# Add to your scraper
from deduplication.smart_deduplicator import SmartDeduplicator

class EnhancedScraper:
    def __init__(self):
        self.deduplicator = SmartDeduplicator(strategy="bloom_and_db")
        self.deduplicator.load_existing_urls()
    
    def scrape_urls(self, urls):
        # Filter out already scraped URLs
        new_urls = self.deduplicator.filter_new_urls(urls)
        
        for url in new_urls:
            try:
                # Your existing scraping logic
                result = self.scrape_single_url(url)
                
                # Mark as successfully scraped
                self.deduplicator.mark_url_scraped(url)
                
            except Exception as e:
                print(f"Failed to scrape {url}: {e}")
```

## 📋 Maintenance Tasks

### Daily
- Monitor duplicate percentage via API
- Check cleanup service logs
- Review error reports

### Weekly
- Run full duplicate analysis
- Clean up old log files
- Update Bloom filter

### Monthly
- Deep content similarity cleanup
- Database optimization
- Performance review

## 🆘 Troubleshooting

### Common Issues

1. **High Memory Usage**
   - Reduce Bloom filter capacity
   - Use Redis for URL caching
   - Process data in smaller batches

2. **Slow Cleanup**
   - Increase batch size
   - Use faster similarity algorithms
   - Skip similar content cleanup for large datasets

3. **False Positives**
   - Reduce Bloom filter error rate
   - Use database verification
   - Manual review of edge cases

### Performance Tuning

```python
# Optimize for speed
deduplicator = SmartDeduplicator(strategy="bloom")

# Optimize for accuracy
deduplicator = SmartDeduplicator(strategy="db")

# Balanced approach
deduplicator = SmartDeduplicator(strategy="bloom_and_db")
```

This deduplication system provides a comprehensive solution for managing duplicate data in your Dark Web Scraper, improving both storage efficiency and scraping performance!
