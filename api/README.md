# Dark Web Scraper API

A FastAPI-based REST API for accessing scraped dark web data stored in OpenSearch.

## Features

- **RESTful API**: Clean, well-documented REST endpoints
- **Search Functionality**: Full-text search through scraped content
- **Pagination**: Efficient pagination for large datasets
- **Filtering & Sorting**: Flexible data retrieval options
- **SSL Support**: Secure connection to OpenSearch with self-signed certificates
- **Auto Documentation**: Interactive API docs with Swagger UI
- **Health Monitoring**: Health check endpoints for monitoring

## Quick Start

### 1. Start the API Service

The API is included in the main docker-compose setup:

```bash
# Start all services including the API
docker compose up -d

# Check API health
curl http://localhost:8000/health
```

### 2. Access API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Health & Stats

- `GET /` - API information
- `GET /health` - Health check
- `GET /stats` - Data statistics

### Data Retrieval

- `GET /documents` - Get all documents with pagination
- `GET /search` - Search through documents
- `GET /document` - Get specific document by URL
- `GET /urls` - Get list of all scraped URLs

## Usage Examples

### Get API Information
```bash
curl http://localhost:8000/
```

### Check Health Status
```bash
curl http://localhost:8000/health
```

### Get Statistics
```bash
curl http://localhost:8000/stats
```

### Get All Documents (Paginated)
```bash
# Get first page (20 documents)
curl "http://localhost:8000/documents"

# Get specific page with custom size
curl "http://localhost:8000/documents?page=2&size=10"

# Include HTML content
curl "http://localhost:8000/documents?include_html=true"

# Sort by URL
curl "http://localhost:8000/documents?sort_field=url&sort_order=asc"
```

### Search Documents
```bash
# Basic search
curl "http://localhost:8000/search?q=bitcoin"

# Search with pagination
curl "http://localhost:8000/search?q=marketplace&page=1&size=5"

# Search with HTML content
curl "http://localhost:8000/search?q=drugs&include_html=true"
```

### Get Specific Document
```bash
curl "http://localhost:8000/document?url=http://example.onion/page"
```

### Get All URLs
```bash
# Get first page of URLs
curl "http://localhost:8000/urls"

# Get specific page
curl "http://localhost:8000/urls?page=2&size=50"
```

## Response Format

### Document Structure
```json
{
  "id": "document_id",
  "url": "http://example.onion/page",
  "text_content": "Extracted text content...",
  "html_content": "Raw HTML content...",
  "timestamp": "2024-01-01T12:00:00Z",
  "score": 1.5
}
```

### Search Response
```json
{
  "documents": [...],
  "total": 150,
  "page": 1,
  "size": 20,
  "total_pages": 8,
  "took": 45
}
```

### Statistics Response
```json
{
  "total_documents": 1500,
  "unique_urls": 450,
  "latest_scrape": "2024-01-01T12:00:00Z",
  "oldest_scrape": "2024-01-01T10:00:00Z",
  "index_size": "2.5 MB"
}
```

## Configuration

The API uses environment variables for configuration:

```env
# OpenSearch connection
OPENSEARCH_HOST=opensearch-node
OPENSEARCH_PORT=9200
OPENSEARCH_SCHEME=https
OPENSEARCH_USER=your_username
OPENSEARCH_PASSWORD=your_password
OPENSEARCH_INDEX=darkweb-content

# API settings
API_HOST=0.0.0.0
API_PORT=8000
```

## Development

### Running Locally

```bash
# Install dependencies
uv sync

# Run the API
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test search functionality
curl "http://localhost:8000/search?q=test"
```

## Security Considerations

- The API connects to OpenSearch using SSL with self-signed certificates
- Authentication is handled through environment variables
- CORS is enabled for development (configure appropriately for production)
- The API runs as a non-root user in the Docker container

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure OpenSearch is running and healthy
2. **SSL Errors**: Check that certificates are properly mounted
3. **Authentication Failed**: Verify OpenSearch credentials in environment variables
4. **No Data**: Ensure the scraper has collected data first

### Logs

```bash
# View API logs
docker compose logs api

# View all service logs
docker compose logs
```
