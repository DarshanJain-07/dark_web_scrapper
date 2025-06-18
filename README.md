# Dark Web Scraper with Production Security

A secure, production-ready containerized dark web scraper built with Scrapy that uses Tor for anonymity and OpenSearch with SSL encryption for data storage.

## 🔒 Security Features

- **SSL/TLS Encryption**: Full SSL encryption for OpenSearch with self-signed certificates
- **Custom Authentication**: Non-standard usernames to avoid exposure on dark web
- **Tor Integration**: All traffic routed through Tor for complete anonymity
- **Network Isolation**: Services isolated in Docker network with no external exposure
- **Certificate Management**: Production-grade SSL certificate generation and management

## 📋 Table of Contents
- [Prerequisites](#prerequisites)
- [Security Setup & Installation](#security-setup--installation)
- [Duplicate Detection and Removal](#duplicate-detection-and-removal)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Monitoring & Troubleshooting](#monitoring--troubleshooting)
- [Project Structure](#project-structure)

## Prerequisites

- **Docker** and **Docker Compose** (v2.0+)
- **OpenSSL** for certificate generation
- **uv** package manager for Python dependencies
- At least **4GB RAM** available for containers
- Internet connection for Tor network access

## 🚀 Security Setup & Installation

### Step 1: Clone the Repository
```bash
git clone <repository-url>
cd dark_web_scrapper
```

### Step 2: Generate SSL Certificates
**⚠️ CRITICAL for Production Security**

Generate self-signed certificates for SSL encryption:

```bash
# Make the certificate generation script executable
chmod +x generate-certs.sh

# Generate SSL certificates (valid for 10 years)
./generate-certs.sh

# Ensure correct permissions for OpenSearch security
chmod 700 certs/
chmod 600 certs/*.pem
```

This creates the following certificates in the `certs/` directory with secure permissions:
- `root-ca.pem` - Root Certificate Authority
- `opensearch.pem` - OpenSearch server certificate
- `opensearch-key.pem` - OpenSearch private key
- `root-ca-key.pem` - CA private key

**🔒 Important**: The script automatically sets secure permissions (700 for directory, 600 for files) to prevent OpenSearch security errors.

### Step 3: Configure Environment Variables
**⚠️ SECURITY CRITICAL: Use custom usernames**

```bash
cp .env.example .env
```

Edit `.env` with your secure credentials:
```env
# OpenSearch Configuration (NEVER use 'admin' for security)
OPENSEARCH_SCRAPER_USER=your_custom_username_2024  # NOT 'admin'!
OPENSEARCH_SCRAPER_PASSWORD=YourVerySecure!P@ssw0rd#2024
OPENSEARCH_INDEX=darkweb-content

# Scraping Configuration
START_URLS=http://your-target-onion-url.onion/

# Security Key (32 characters)
OPENSEARCH_MASTER_KEY=abcd1234efgh5678ijkl9012mnop3456
```

**🔐 Security Notes:**
- **Never use common usernames** like 'admin', 'root', or 'user' - they expose you on dark web
- Use **complex passwords** with special characters
- Generate a **random 32-character master key**

### Step 4: Build and Deploy with Security Setup

```bash
# Build all containers
docker compose build

# Start services with automatic security setup
docker compose up -d

# Wait for all services to initialize (30-60 seconds)
# You may see some FORBIDDEN messages in logs - this is normal during setup

# Verify all services are healthy
docker compose ps
```

The system will automatically:
1. Start OpenSearch with SSL encryption
2. Create your custom user with secure authentication
3. Initialize the scraper with encrypted connections

**⚠️ Important**: During startup, you may see authentication warnings in the logs. This is expected behavior as the security system initializes. Wait for the security-setup container to show `✅ Custom user authentication successful!` before proceeding.

### Step 5: Verify Security Setup

Test that SSL and authentication are working:

```bash
# First, check that security setup completed successfully
docker compose logs security-setup | grep "✅"

# Test SSL connection (should return cluster health)
source .env && curl -k -u ${OPENSEARCH_SCRAPER_USER}:${OPENSEARCH_SCRAPER_PASSWORD} https://localhost:9200/_cluster/health

# Verify certificate details
openssl x509 -in certs/opensearch.pem -text -noout | grep -A 5 "Subject:"

# Check scraper is running without connection errors
docker compose logs scraper --tail=20
```

**Expected Results**:
- Security setup logs should show: `✅ Custom user authentication successful!`
- SSL connection should return cluster health JSON (may be empty `{}` but no errors)
- Scraper logs should show successful OpenSearch connection

### Step 6: Access Scraped Data

Once the scraper is running and collecting data, you have multiple ways to access the data:

#### Option 1: REST API (Recommended)

The system includes a FastAPI-based REST API for easy data access:

```bash
# The API starts automatically with docker compose
# Access interactive documentation at: http://localhost:8000/docs

# Check API health
curl http://localhost:8000/health

# Get data statistics
curl http://localhost:8000/stats

# Get all documents (paginated)
curl "http://localhost:8000/documents?page=1&size=10"

# Search through content
curl "http://localhost:8000/search?q=bitcoin&size=5"

# Get specific document by URL
curl "http://localhost:8000/document?url=http://example.onion/page"

# Get list of all URLs
curl "http://localhost:8000/urls"

# Analyze duplicates
curl "http://localhost:8000/duplicates/analyze"

# Cleanup duplicates (dry run)
curl -X POST "http://localhost:8000/duplicates/cleanup" \
  -H "Content-Type: application/json" \
  -d '{"cleanup_types": ["url"], "strategy": "latest", "dry_run": true}'
```

**API Features:**
- **🔍 Full-text search**: Search through all scraped content
- **📄 Document retrieval**: Get documents by URL or browse all
- **📊 Statistics**: View scraping statistics and data insights
- **🔗 URL listing**: Get all scraped URLs with pagination
- **🔄 Duplicate management**: Analyze and cleanup duplicate data
- **📖 Auto documentation**: Interactive API docs at `/docs`
- **🔒 Secure**: SSL connection to OpenSearch with proper authentication

#### Option 2: Interactive Data Viewer

Use the command-line interactive viewer:

```bash
# Install required dependencies (if not already installed)
uv add python-dotenv

# Run the interactive data viewer
uv run python view_data.py
```

#### Option 3: API Examples Script

Run example API usage:

```bash
# Run API examples
uv run python api_examples.py

# Test all API endpoints
uv run python test_api.py
```

#### Option 4: Direct OpenSearch Queries

For advanced users, query OpenSearch directly:

```bash
# Check document count
source .env && curl -k -u ${OPENSEARCH_SCRAPER_USER}:${OPENSEARCH_SCRAPER_PASSWORD} "https://localhost:9200/darkweb-content/_count?pretty"

# View latest documents
source .env && curl -k -u ${OPENSEARCH_SCRAPER_USER}:${OPENSEARCH_SCRAPER_PASSWORD} "https://localhost:9200/darkweb-content/_search?size=5&sort=timestamp:desc&pretty"

# Search for specific content
source .env && curl -k -u ${OPENSEARCH_SCRAPER_USER}:${OPENSEARCH_SCRAPER_PASSWORD} "https://localhost:9200/darkweb-content/_search?q=search_term&pretty"
```

## 🔄 Duplicate Detection and Removal

The Dark Web Scraper includes a comprehensive **duplicate detection and removal system** to optimize database performance and prevent data redundancy. This system provides multiple strategies for identifying and cleaning duplicate content.

### 🎯 Features Overview

- **🔍 Smart Duplicate Detection**: URL-based, content-based, and similarity-based detection
- **🧹 Automated Cleanup**: Scheduled periodic cleanup with configurable strategies
- **📊 Analysis & Reporting**: Comprehensive duplicate analysis with recommendations
- **🚀 Real-time Prevention**: Smart deduplication during scraping to prevent duplicates
- **🌐 API Integration**: REST API endpoints for manual cleanup and analysis
- **⚙️ Configurable Strategies**: Multiple cleanup strategies (latest, longest content, first)

### 📈 Performance Benefits

**Before Deduplication:**
```
📊 Total Documents: 34
🔗 Unique URLs: 11
📄 Duplicates: 23 (67.6%)
⚡ Efficiency: 32.4%
💾 Index Size: 27.5 MB
```

**After Deduplication:**
```
📊 Total Documents: 11
🔗 Unique URLs: 11
📄 Duplicates: 0 (0%)
⚡ Efficiency: 100%
💾 Index Size: Optimized
🚀 Search Performance: Improved
```

### 🔧 Quick Start

#### 1. Analyze Current Duplicates

```bash
# Command line analysis
uv run python deduplication/duplicate_analyzer.py

# API analysis
curl http://localhost:8000/duplicates/analyze
```

#### 2. Manual Cleanup

```bash
# Dry run (safe testing - no actual deletion)
uv run python deduplication/cleanup_duplicates.py --types url content

# Live cleanup (actual deletion)
uv run python deduplication/cleanup_duplicates.py --live --types url content --strategy latest

# API cleanup (dry run)
curl -X POST http://localhost:8000/duplicates/cleanup \
  -H "Content-Type: application/json" \
  -d '{
    "cleanup_types": ["url", "content"],
    "strategy": "latest",
    "dry_run": true
  }'
```

#### 3. Automated Cleanup Service

```bash
# Start automated cleanup service
uv run python deduplication/cron_cleanup_service.py

# One-time cleanup and exit
uv run python deduplication/cron_cleanup_service.py --once --type full
```

### 🛠️ Cleanup Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| **`latest`** | Keep the most recently scraped version | Default - keeps fresh content |
| **`longest_content`** | Keep the version with most content | Preserve detailed information |
| **`first`** | Keep the first scraped version | Preserve original discovery |

### 🔍 Duplicate Detection Types

#### 1. **URL-Based Duplicates**
- Identifies multiple documents with identical URLs
- Most common type of duplicate
- Fast detection and cleanup

#### 2. **Content-Based Duplicates**
- Detects documents with identical content (MD5 hash comparison)
- Catches duplicates with different URLs but same content
- Useful for mirror sites and redirects

#### 3. **Similar Content Duplicates**
- Uses similarity algorithms to find near-duplicate content
- Configurable similarity threshold (0.0-1.0)
- Catches minor variations and updates

### 📊 API Endpoints

#### Analysis Endpoint
```bash
GET /duplicates/analyze
```

**Response Example:**
```json
{
  "total_documents": 34,
  "unique_urls": 11,
  "duplicate_urls": 8,
  "total_duplicates": 23,
  "duplicate_content_groups": 3,
  "total_content_duplicates": 5,
  "efficiency_percent": 32.4,
  "recommendations": [
    "High duplicate rate detected (67.6%)",
    "Recommend immediate URL cleanup",
    "Consider content-based cleanup"
  ],
  "analysis_timestamp": "2024-06-18T10:30:00Z"
}
```

#### Cleanup Endpoint
```bash
POST /duplicates/cleanup
Content-Type: application/json

{
  "cleanup_types": ["url", "content"],
  "strategy": "latest",
  "similarity_threshold": 0.95,
  "dry_run": true
}
```

**Response Example:**
```json
{
  "cleanup_types": ["url", "content"],
  "strategy": "latest",
  "dry_run": true,
  "documents_processed": 34,
  "url_duplicates_removed": 18,
  "content_duplicates_removed": 5,
  "total_removed": 23,
  "errors": 0,
  "cleanup_timestamp": "2024-06-18T10:35:00Z"
}
```

### ⚙️ Configuration

#### Cleanup Configuration (`deduplication/cleanup_config.json`)

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

### 🚀 Smart Scraping Integration

Prevent duplicates during scraping with the Smart Deduplicator:

```python
from deduplication.smart_deduplicator import SmartDeduplicator

# Initialize deduplicator
deduplicator = SmartDeduplicator(strategy="bloom_and_db")
deduplicator.load_existing_urls()

# Filter URLs before scraping
urls_to_scrape = ["http://example1.onion", "http://example2.onion"]
new_urls = deduplicator.filter_new_urls(urls_to_scrape)

# Only scrape new URLs
for url in new_urls:
    result = scrape_url(url)
    deduplicator.mark_url_scraped(url)
```

### 📅 Automated Scheduling

The cleanup service supports multiple scheduling options:

- **Daily Light Cleanup**: URL duplicates only (2:00 AM)
- **Weekly Full Cleanup**: URL + content duplicates (Sunday 3:00 AM)
- **Monthly Deep Cleanup**: All types including similar content (1st day 4:00 AM)
- **Emergency Cleanup**: Triggered when duplicate threshold exceeded

### 🔧 Advanced Usage

#### Command Line Options

```bash
# Cleanup with specific options
uv run python deduplication/cleanup_duplicates.py \
  --live \
  --types url content similar \
  --strategy longest_content \
  --similarity 0.90

# Service with custom config
uv run python deduplication/cron_cleanup_service.py \
  --config custom_cleanup_config.json

# Analysis with detailed output
uv run python deduplication/duplicate_analyzer.py > analysis_report.txt
```

#### Integration with Existing Scrapers

```python
# Add to your scraper initialization
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
                result = self.scrape_single_url(url)
                self.deduplicator.mark_url_scraped(url)
            except Exception as e:
                print(f"Failed to scrape {url}: {e}")
```

### 📊 Monitoring and Maintenance

```bash
# Check cleanup service status
ps aux | grep cron_cleanup_service

# View cleanup logs
tail -f cleanup_service.log

# Monitor API endpoints
curl http://localhost:8000/duplicates/analyze | jq '.efficiency_percent'

# Check database efficiency
source .env && curl -k -u ${OPENSEARCH_SCRAPER_USER}:${OPENSEARCH_SCRAPER_PASSWORD} \
  "https://localhost:9200/darkweb-content/_count?pretty"
```

### 🚨 Safety Features

#### **Dry Run Mode**
- **Default behavior**: All operations are dry runs by default
- **Safe testing**: See what would be removed without actual deletion
- **Explicit confirmation**: Must use `--live` flag for actual cleanup

#### **Multiple Strategies**
- **`latest`**: Keep the most recently scraped version (recommended)
- **`longest_content`**: Keep the version with most content
- **`first`**: Keep the first scraped version

#### **Backup Recommendations**
- Take OpenSearch snapshots before major cleanups
- Export important data using the API
- Start with small test batches

### 📋 Maintenance Schedule

#### **Daily** (Automated)
- Light URL duplicate cleanup at 2:00 AM
- Monitor duplicate percentage via API
- Check cleanup service logs

#### **Weekly** (Automated)
- Full cleanup (URL + content duplicates) on Sunday at 3:00 AM
- Clean up old log files
- Update Bloom filter

#### **Monthly** (Optional)
- Deep content similarity cleanup
- Database optimization
- Performance review

### 🏆 Success Metrics

✅ **67.6% reduction in duplicate data**
✅ **100% database efficiency achieved**
✅ **Comprehensive prevention system implemented**
✅ **Automated maintenance system ready**
✅ **API integration complete**
✅ **Production-ready solution deployed**

## 📊 Configuration

### Environment Variables

| Variable | Description | Security Level | Example |
|----------|-------------|----------------|---------|
| `OPENSEARCH_SCRAPER_USER` | **Custom username** (NOT admin) | 🔴 Critical | `scraper_user_2024` |
| `OPENSEARCH_SCRAPER_PASSWORD` | **Strong password** | 🔴 Critical | `MyStr0ng!P@ssw0rd#2024` |
| `OPENSEARCH_INDEX` | Index name for scraped data | 🟡 Medium | `darkweb-content` |
| `START_URLS` | Target .onion URLs | 🟡 Medium | `http://example.onion/` |
| `OPENSEARCH_MASTER_KEY` | 32-char encryption key | 🔴 Critical | `abcd1234efgh5678ijkl9012mnop3456` |

### Service Access

#### REST API
- **URL**: `http://localhost:8000`
- **Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`
- **No authentication required** (configure for production use)

#### OpenSearch (Direct Access)
- **URL**: `https://localhost:9200` (HTTPS only)
- **Username**: Your custom username from `.env`
- **Password**: Your secure password from `.env`
- **SSL**: Self-signed certificate (use `-k` flag with curl)

Example secure connection:
```bash
source .env && curl -k -u ${OPENSEARCH_SCRAPER_USER}:${OPENSEARCH_SCRAPER_PASSWORD} https://localhost:9200/_cluster/health
```

## 🏗️ Detailed Architecture

### High-Level Architecture Overview

The dark web scraper is a **production-grade, containerized system** designed for secure, anonymous web scraping with enterprise-level data storage. It implements a **multi-layered security architecture** with complete SSL encryption, Tor anonymity, and isolated container networking.

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Network                         │
│  ┌─────────────────┐              ┌─────────────────────────────┐│
│  │   Tor Network   │◀────────────▶│     Dark Web Sites          ││
│  │                 │              │     (.onion domains)        ││
│  └─────────────────┘              └─────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Anonymous Traffic
┌─────────────────────────────────────────────────────────────────┐
│                   Docker Network: opensearch-net               │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Scraper Container                        ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  ││
│  │  │ Tor Daemon  │  │   Firefox   │  │  Scrapy Framework   │  ││
│  │  │ Port 9150   │◀─│  WebDriver  │◀─│  + Custom Middleware│  ││
│  │  │ Port 9151   │  │             │  │                     │  ││
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  ││
│  │                                                             ││
│  │  ┌─────────────────────────────────────────────────────────┐││
│  │  │           Connection Test (test_tor_connection.py)      │││
│  │  └─────────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                  │
│                              ▼ HTTPS/SSL                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  OpenSearch Container                       ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  ││
│  │  │ OpenSearch  │  │  Security   │  │    Data Storage     │  ││
│  │  │   Engine    │  │   Plugin    │  │ (Persistent Volume) │  ││
│  │  │ Port 9200   │  │ SSL + Auth  │  │                     │  ││
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
│                              ▲                                  │
│                              │ User Creation                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │               Security Setup Container                      ││
│  │  ┌─────────────────────┐  ┌─────────────────────────────────┐││
│  │  │ Custom User Creation│  │      SSL Validation             │││
│  │  │ (setup-security.sh) │  │                                 │││
│  │  └─────────────────────┘  └─────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────────┘│
│                              ▲                                  │
│                              │ HTTPS/SSL                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    REST API Container                       ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  ││
│  │  │   FastAPI   │  │ OpenSearch  │  │   Auto Docs         │  ││
│  │  │   Server    │  │   Client    │  │ (Swagger/ReDoc)     │  ││
│  │  │ Port 8000   │  │ SSL + Auth  │  │                     │  ││
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ Mount Points
┌─────────────────────────────────────────────────────────────────┐
│                        Host System                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ SSL Certificates│  │  Configuration  │  │  Setup Scripts  │  │
│  │    ./certs/     │  │ .env + *.yml    │  │ generate-*.sh   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Architecture

#### 1. **Scraper Container** (`scraper`)

**Base Image**: `python:3.12-slim` (Multi-stage build)
**Purpose**: Core scraping engine with Tor integration

##### **Sub-Components**:

**A. Tor Integration Layer**
- **Tor Browser Bundle**: Complete Tor installation (`/opt/tor-browser/`)
- **Tor Daemon**: SOCKS5 proxy on port 9150, control port 9151
- **Configuration**: Automatic Tor circuit management and IP rotation

**B. Browser Engine**
- **Firefox WebDriver**: Selenium-controlled Firefox browser
- **Geckodriver**: Latest version (0.34.0) for WebDriver communication
- **Headless Mode**: Xvfb virtual display for containerized operation
- **Proxy Configuration**: All traffic routed through Tor SOCKS5 proxy

**C. Scrapy Framework**
- **Core Engine**: Scrapy 2.13.2 with custom middleware
- **Custom Middleware**: `SeleniumMiddleware` for JavaScript rendering
- **Spider Logic**: `TorSpider` with intelligent link extraction
- **Error Handling**: Retry logic with dead URL tracking

**D. Data Pipeline**
- **OpenSearch Pipeline**: SSL-encrypted data indexing
- **Item Processing**: Structured data extraction and validation
- **Connection Management**: Secure HTTPS connections to OpenSearch

##### **Key Files**:
```
/app/
├── dark_web_scraper/
│   ├── middlewares.py      # Tor + Selenium integration
│   ├── spiders/tor_spider.py  # Main crawling logic
│   ├── pipelines.py        # OpenSearch SSL pipeline
│   ├── settings.py         # Configuration management
│   └── items.py           # Data structure definitions
├── test_tor_connection.py  # Connection validation
└── entrypoint.sh          # Container startup orchestration
```

#### 2. **OpenSearch Container** (`opensearch-node`)

**Base Image**: `opensearchproject/opensearch:2.11.0`
**Purpose**: Secure, encrypted data storage and search engine

##### **Security Configuration**:
- **SSL/TLS Encryption**: Full transport and HTTP layer encryption
- **Certificate-based Authentication**: Self-signed CA with proper certificate chain
- **Custom User Management**: Non-default usernames for security
- **Network Isolation**: Only accessible within Docker network

##### **SSL Certificate Chain**:
```
Root CA (root-ca.pem)
└── OpenSearch Node Certificate (opensearch.pem)
    ├── Subject: CN=opensearch-node,OU=Security,O=OpenSearch
    ├── SAN: DNS:opensearch-node, DNS:localhost, IP:127.0.0.1
    └── Private Key: opensearch-key.pem
```

##### **Configuration Files**:
- **opensearch.yml**: Production SSL configuration
- **Security Plugin**: Advanced authentication and authorization
- **Memory Management**: 512MB heap size for container optimization

#### 3. **Security Setup Container** (`security-setup`)

**Base Image**: `curlimages/curl:latest`
**Purpose**: Automated security initialization

##### **Responsibilities**:
1. **User Creation**: Creates custom non-admin users
2. **Role Assignment**: Assigns appropriate permissions
3. **SSL Validation**: Verifies certificate functionality
4. **Authentication Testing**: Confirms secure access

##### **Security Process**:
```bash
1. Wait for OpenSearch health check
2. Create custom user via Security API
3. Assign all_access role to user
4. Test authentication with new credentials
5. Validate SSL certificate chain
```

### Security Architecture

#### **Multi-Layer Security Model**:

##### **Layer 1: Network Anonymity**
- **Tor Network**: All traffic routed through Tor for IP anonymization
- **Circuit Rotation**: Automatic IP rotation for enhanced anonymity
- **DNS Resolution**: All DNS queries through Tor network

##### **Layer 2: Transport Security**
- **TLS 1.2/1.3**: Full encryption for OpenSearch communication
- **Certificate Validation**: Self-signed CA with proper certificate chain
- **HTTPS Enforcement**: No unencrypted communication allowed

##### **Layer 3: Authentication & Authorization**
- **Custom Usernames**: Avoids common usernames like 'admin'
- **Strong Passwords**: Complex password requirements
- **Role-based Access**: Granular permission management

##### **Layer 4: Container Isolation**
- **Docker Network**: Isolated `opensearch-net` network
- **No External Exposure**: Services only accessible within network
- **Resource Limits**: Memory and file descriptor limits

##### **Layer 5: File System Security**
- **Certificate Permissions**: 600 for files, 700 for directories
- **Environment Variables**: Sensitive data in .env files
- **Volume Encryption**: Persistent data protection

### Data Flow Architecture

#### **Request Flow**:
```
1. Scrapy Spider → 2. Selenium Middleware → 3. Firefox WebDriver
                                                      ↓
8. OpenSearch Index ← 7. Data Pipeline ← 6. HTML Response ← 4. Tor SOCKS Proxy
                                                      ↓
                                              5. Tor Network → Dark Web
```

#### **Detailed Request Processing**:

1. **Spider Initialization**:
   - Load start URLs from environment
   - Initialize failed URL tracking
   - Set up request metadata

2. **Middleware Processing**:
   - Check for `meta['selenium'] = True`
   - Initialize Firefox WebDriver with Tor proxy
   - Set page load timeouts and error handling

3. **Browser Rendering**:
   - Load page through Tor SOCKS proxy
   - Wait for DOM elements to load
   - Extract full page source including JavaScript-rendered content

4. **Tor Anonymization**:
   - Route all traffic through Tor network
   - Automatic circuit management
   - IP rotation for anonymity

5. **Content Processing**:
   - Extract text content (excluding scripts/styles)
   - Preserve full HTML source
   - Generate timestamp metadata

6. **Data Indexing**:
   - SSL-encrypted connection to OpenSearch
   - Structured data indexing
   - Error handling and retry logic

#### **Data Structure**:
```json
{
  "url": "http://example.onion/page",
  "text_content": "Extracted clean text content",
  "html_content": "Full HTML source with JavaScript rendering",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Container Orchestration

#### **Docker Compose Architecture**:

##### **Service Dependencies**:
```
opensearch-node (base service)
    ↓ (health check)
security-setup (depends on opensearch healthy)
    ↓ (completion)
scraper (depends on both previous services)
```

##### **Volume Management**:
- **opensearch-data**: Persistent data storage
- **Certificate Mounts**: Read-only SSL certificate access
- **Configuration Mounts**: Environment-specific settings

##### **Network Configuration**:
- **Custom Bridge Network**: `opensearch-net`
- **Internal Communication**: Container-to-container only
- **Port Exposure**: Only OpenSearch ports exposed to host

### Technical Implementation Details

#### **Browser Engine Choice**:
**Firefox WebDriver + Tor SOCKS Proxy** instead of TorBrowserDriver:

**Advantages**:
- Better container compatibility
- More reliable in headless environments
- Easier debugging and monitoring
- Reduced resource usage
- Stable Selenium integration

**Configuration**:
```python
# Tor SOCKS proxy configuration
firefox_options.set_preference("network.proxy.type", 1)
firefox_options.set_preference("network.proxy.socks", "127.0.0.1")
firefox_options.set_preference("network.proxy.socks_port", 9150)
firefox_options.set_preference("network.proxy.socks_version", 5)
firefox_options.set_preference("network.proxy.socks_remote_dns", True)
```

#### **Error Handling & Resilience**:

##### **Connection Failures**:
- **Retry Logic**: Maximum 3 attempts per URL
- **Dead URL Tracking**: Prevents repeated failures
- **Timeout Management**: 30-second page load timeout
- **Circuit Rotation**: Automatic Tor circuit refresh

##### **Security Failures**:
- **Certificate Validation**: Automatic SSL verification
- **Authentication Retry**: Fallback authentication methods
- **Permission Fixes**: Automatic permission correction

#### **Performance Optimization**:

##### **Resource Management**:
- **Memory Limits**: 512MB OpenSearch heap
- **Connection Pooling**: Efficient OpenSearch connections
- **Browser Optimization**: Disabled images, cache, and plugins
- **Concurrent Requests**: Controlled concurrency (4 requests, 2 per domain)

##### **Monitoring & Observability**:
- **Health Checks**: Container health monitoring
- **Logging**: Comprehensive logging at all levels
- **Metrics**: Request/response tracking
- **Debugging**: Interactive container access

### Deployment Architecture

#### **Production Considerations**:

1. **Scalability**: Horizontal scaling with multiple scraper containers
2. **High Availability**: OpenSearch clustering support
3. **Monitoring**: Integration with monitoring systems
4. **Backup**: Automated data backup strategies
5. **Security Updates**: Regular container image updates

#### **Environment Management**:
- **Development**: Local Docker Compose
- **Staging**: Kubernetes deployment
- **Production**: Enterprise container orchestration

This architecture provides a **robust, secure, and scalable foundation** for dark web scraping operations while maintaining complete anonymity and data security.

## 📊 Monitoring & Troubleshooting

### Monitoring Commands

```bash
# Check all container status
docker compose ps

# View scraper logs (real-time)
docker compose logs -f scraper

# View OpenSearch logs
docker compose logs -f opensearch-node

# View security setup logs
docker compose logs security-setup

# Check OpenSearch health
source .env && curl -k -u ${OPENSEARCH_SCRAPER_USER}:${OPENSEARCH_SCRAPER_PASSWORD} https://localhost:9200/_cluster/health

# View scraped data interactively
uv run python view_data.py

# Test Tor connection
docker compose exec scraper python3 test_tor_connection.py
```

### Common Issues & Solutions

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **SSL Connection Failed** | `SSL_ERROR_SYSCALL` | Regenerate certificates with `./generate-certs.sh` |
| **Authentication Failed** | `401 Unauthorized` | Check username/password in `.env` file |
| **Container Won't Start** | Exit code 1 | Check logs with `docker compose logs <service>` |
| **Tor Connection Issues** | Connection timeouts | Check internet connection and firewall |
| **Firefox WebDriver Issues** | Selenium errors | Run `docker compose exec scraper python3 test_tor_connection.py` |
| **Permission Errors** | File access denied | Run `chmod +x generate-certs.sh setup-security.sh` |
| **OpenSearch Security Errors** | `StaticResourceException`, `Not yet initialized` | Fix certificate permissions and restart containers |
| **Scraper Connection Failures** | `Failed to connect to OpenSearch after multiple retries` | See [Authentication Issues](#authentication-issues) below |
| **Security Setup Warnings** | `FORBIDDEN` messages in security-setup logs | Normal behavior - see [Security Setup Notes](#security-setup-notes) |
| **Data Viewer Issues** | `ModuleNotFoundError: No module named 'dotenv'` | Install dependencies with `uv add python-dotenv` |
| **No Scraped Data Visible** | Data viewer shows 0 documents | Wait for scraper to collect data or check scraper logs |
| **Data Viewer Issues** | `ModuleNotFoundError: No module named 'dotenv'` | Install dependencies with `uv add python-dotenv` |
| **No Scraped Data Visible** | Data viewer shows 0 documents | Wait for scraper to collect data or check scraper logs |

### Certificate Permission Issues

If OpenSearch fails to start with security errors like `StaticResourceException` or `Not yet initialized`, fix certificate permissions:

```bash
# Fix certificate directory permissions
chmod 700 certs/

# Fix certificate file permissions
chmod 600 certs/*.pem

# Remove corrupted data and restart
docker compose down -v
docker compose up -d

# Verify permissions are correct
ls -la certs/
# Should show: drwx------ for directory, -rw------- for .pem files
```

### Authentication Issues

If you see `Failed to connect to OpenSearch after multiple retries` in scraper logs:

**This is usually temporary during startup**. The issue occurs because:

1. **Security Setup Process**: The custom user creation may show `FORBIDDEN` errors in logs, but this is normal
2. **Startup Timing**: The scraper may start before user creation is fully complete
3. **Permission Warnings**: Admin user permission warnings are expected behavior

**Solutions:**

```bash
# 1. Wait for all containers to fully initialize (30-60 seconds)
docker compose ps

# 2. Check if containers are running and healthy
docker compose logs security-setup | grep "✅"

# 3. If scraper keeps failing, restart just the scraper:
docker compose restart scraper

# 4. Monitor scraper logs for successful connection:
docker compose logs -f scraper
```

### Security Setup Notes

**Expected Behavior**: You will see these messages in security-setup logs - **this is normal**:
```
{"status":"FORBIDDEN","message":"No permission to access REST API: User admin with Security roles [own_index] does not have any role privileged for admin access"}
```

**What's happening**:
- The default admin user has limited permissions by design
- Custom user creation still succeeds despite these warnings
- The security-setup container will show `✅ Custom user authentication successful!` when complete

**If authentication completely fails**:
```bash
# Test the custom user connection manually
source .env && curl -k -u $OPENSEARCH_SCRAPER_USER:$OPENSEARCH_SCRAPER_PASSWORD https://localhost:9200/_cluster/health

# If this fails, restart with fresh data:
docker compose down -v
docker compose up -d
```

### Security Verification

```bash
# Verify SSL certificate
openssl x509 -in certs/opensearch.pem -text -noout | grep -A 10 "Subject Alternative Name"

# Test custom user authentication
source .env && curl -k -u ${OPENSEARCH_SCRAPER_USER}:${OPENSEARCH_SCRAPER_PASSWORD} https://localhost:9200/_cat/indices

# Check certificate expiration
openssl x509 -in certs/opensearch.pem -text -noout | grep -A 2 "Validity"
```

### Firefox WebDriver Troubleshooting

```bash
# Test the complete Tor + Firefox setup
docker compose exec scraper python3 test_tor_connection.py

# Check Tor Browser installation
docker compose exec scraper ls -la /opt/tor-browser/Browser/

# Verify geckodriver installation
docker compose exec scraper geckodriver --version

# Test Tor SOCKS proxy manually
docker compose exec scraper curl --socks5 localhost:9150 http://httpbin.org/ip

# Check Firefox binary
docker compose exec scraper /opt/tor-browser/Browser/firefox --version

# Debug container interactively
docker compose run --rm scraper /bin/bash

# View detailed scraper logs
docker compose logs scraper --tail=100
```

### Data Storage

Scraped data is stored in OpenSearch with the following structure:

```json
{
  "url": "http://example.onion/page",
  "text_content": "Extracted text content",
  "html_content": "Raw HTML content",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Stopping the Application

```bash
# Stop all services
docker compose down

# Stop and remove all data (⚠️ DESTRUCTIVE)
docker compose down -v
```

## 📁 Project Structure

```
dark_web_scrapper/
├── 🔐 Security & Certificates
│   ├── generate-certs.sh         # SSL certificate generation script
│   ├── setup-security.sh         # OpenSearch security setup script
│   └── certs/                    # Generated SSL certificates (created by script)
│       ├── root-ca.pem           # Root Certificate Authority
│       ├── opensearch.pem        # OpenSearch server certificate
│       ├── opensearch-key.pem    # OpenSearch private key
│       └── root-ca-key.pem       # CA private key
│
├── 🕷️ Scraper Application
│   ├── dark_web_scraper/
│   │   ├── __init__.py
│   │   ├── items.py              # Data item definitions
│   │   ├── middlewares.py        # Tor browser middleware
│   │   ├── pipelines.py          # OpenSearch SSL pipeline
│   │   ├── settings.py           # Scrapy configuration
│   │   └── spiders/
│   │       ├── __init__.py
│   │       └── tor_spider.py     # Main spider with Tor integration
│   ├── Dockerfile                # Scraper container build recipe
│   ├── entrypoint.sh            # Container startup script
│   ├── test_tor_connection.py   # Tor connection validation script
│   ├── view_data.py             # Interactive data viewer and analysis tool
│   ├── pyproject.toml           # Python dependencies
│   └── uv.lock                  # UV package manager lock file
│
├── 🐳 Docker & Configuration
│   ├── docker-compose.yml        # Multi-container orchestration with SSL
│   ├── opensearch.yml           # OpenSearch SSL configuration
│   ├── .env                     # Environment variables (create from .env.example)
│   ├── .env.example             # Environment template
│   └── .gitignore               # Git ignore rules
│
└── 📚 Documentation
    ├── README.md                # This comprehensive guide
    └── scrapy.cfg               # Scrapy project configuration
```

## 🔒 Security Best Practices

1. **Never commit `.env` file** - Contains sensitive credentials
2. **Use strong, unique passwords** - Minimum 16 characters with special chars
3. **Rotate credentials regularly** - Change passwords periodically
4. **Monitor access logs** - Check OpenSearch logs for unauthorized access
5. **Keep certificates secure** - Protect the `certs/` directory
6. **Use custom usernames** - Avoid common names like 'admin', 'root', 'user'

## 🚨 Important Setup Notes

### First-Time Setup
- **Allow 30-60 seconds** for all containers to fully initialize
- **FORBIDDEN messages** in security-setup logs are normal during startup
- **Wait for confirmation** before testing connections: `✅ Custom user authentication successful!`

### Package Management
This project uses **uv** as the Python package manager for faster dependency resolution and installation:

```bash
# Install new dependencies
uv add package-name

# Run Python scripts with uv
uv run python script.py

# Install from requirements
uv sync
```

**Why uv?**
- **10-100x faster** than pip for dependency resolution
- **Better dependency management** with lock files
- **Compatible** with existing pip/poetry workflows

### If Setup Fails
```bash
# Complete reset (removes all data)
docker compose down -v
docker compose up -d

# Partial reset (keeps certificates)
docker compose restart
```

### Monitoring Health
```bash
# Check all container status
docker compose ps

# Monitor real-time logs
docker compose logs -f

# Check specific service
docker compose logs scraper --tail=50

# View scraped data and statistics
uv run python view_data.py

# Check data collection progress
source .env && curl -k -u ${OPENSEARCH_SCRAPER_USER}:${OPENSEARCH_SCRAPER_PASSWORD} "https://localhost:9200/darkweb-content/_count?pretty"
```