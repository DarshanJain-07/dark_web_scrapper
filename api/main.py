"""
FastAPI application for serving scraped dark web data.

This API provides endpoints to access and search through data
scraped from dark web sites and stored in OpenSearch.
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import os
from datetime import datetime
import logging

from .config import get_settings
from .opensearch_client import OpenSearchClient
from .models import (
    ScrapedDocument,
    SearchResponse,
    DocumentResponse,
    HealthResponse,
    StatsResponse,
    URLListResponse,
    DuplicateAnalysisResponse,
    CleanupResponse,
    CleanupRequest
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Dark Web Scraper API",
    description="API for accessing scraped dark web data stored in OpenSearch",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get OpenSearch client
def get_opensearch_client() -> OpenSearchClient:
    """Get OpenSearch client instance."""
    settings = get_settings()
    return OpenSearchClient(settings)

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Dark Web Scraper API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check(client: OpenSearchClient = Depends(get_opensearch_client)):
    """Health check endpoint."""
    try:
        is_healthy = await client.health_check()
        return HealthResponse(
            status="healthy" if is_healthy else "unhealthy",
            timestamp=datetime.utcnow(),
            opensearch_connected=is_healthy
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            opensearch_connected=False,
            error=str(e)
        )

@app.get("/stats", response_model=StatsResponse)
async def get_stats(client: OpenSearchClient = Depends(get_opensearch_client)):
    """Get statistics about the scraped data."""
    try:
        stats = await client.get_stats()
        return StatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/documents", response_model=SearchResponse)
async def get_documents(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Number of results per page"),
    sort_field: str = Query("timestamp", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    include_html: bool = Query(False, description="Include HTML content in results"),
    client: OpenSearchClient = Depends(get_opensearch_client)
):
    """Get all scraped documents with pagination."""
    try:
        documents, total = await client.get_all_documents(
            page=page,
            size=size,
            sort_field=sort_field,
            sort_order=sort_order,
            include_html=include_html
        )

        total_pages = (total + size - 1) // size

        return SearchResponse(
            documents=documents,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
            took=0  # Not applicable for get_all
        )
    except Exception as e:
        logger.error(f"Failed to get documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get documents: {str(e)}")

@app.get("/search", response_model=SearchResponse)
async def search_documents(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Number of results per page"),
    sort_field: str = Query("_score", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    include_html: bool = Query(False, description="Include HTML content in results"),
    client: OpenSearchClient = Depends(get_opensearch_client)
):
    """Search through scraped documents."""
    try:
        documents, total, took = await client.search_documents(
            query=q,
            page=page,
            size=size,
            sort_field=sort_field,
            sort_order=sort_order,
            include_html=include_html
        )

        total_pages = (total + size - 1) // size

        return SearchResponse(
            documents=documents,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
            took=took
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/document", response_model=DocumentResponse)
async def get_document_by_url(
    url: str = Query(..., description="URL of the document to retrieve"),
    include_html: bool = Query(False, description="Include HTML content in response"),
    client: OpenSearchClient = Depends(get_opensearch_client)
):
    """Get a specific document by its URL."""
    try:
        document = await client.get_document_by_url(url, include_html=include_html)

        if document:
            return DocumentResponse(document=document, found=True)
        else:
            return DocumentResponse(
                document=ScrapedDocument(
                    url="",
                    text_content="",
                    timestamp=datetime.utcnow()
                ),
                found=False
            )
    except Exception as e:
        logger.error(f"Failed to get document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")

@app.get("/urls", response_model=URLListResponse)
async def get_urls(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=100, description="Number of URLs per page"),
    client: OpenSearchClient = Depends(get_opensearch_client)
):
    """Get list of all scraped URLs."""
    try:
        urls, total = await client.get_urls(page=page, size=size)
        total_pages = (total + size - 1) // size

        return URLListResponse(
            urls=urls,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Failed to get URLs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get URLs: {str(e)}")

@app.get("/duplicates/analyze", response_model=DuplicateAnalysisResponse)
async def analyze_duplicates():
    """Analyze duplicate data patterns."""
    try:
        # Import here to avoid circular imports
        import sys
        import os

        # Add the project root to Python path
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        deduplication_path = os.path.join(project_root, 'deduplication')
        if deduplication_path not in sys.path:
            sys.path.insert(0, deduplication_path)

        from duplicate_analyzer import DuplicateAnalyzer

        analyzer = DuplicateAnalyzer()
        results = analyzer.run_full_analysis()

        url_analysis = results['url_analysis']
        content_analysis = results['content_analysis']

        # Calculate efficiency
        efficiency = 0
        if url_analysis['total_documents'] > 0:
            efficiency = (url_analysis['unique_urls'] / url_analysis['total_documents']) * 100

        return DuplicateAnalysisResponse(
            total_documents=url_analysis['total_documents'],
            unique_urls=url_analysis['unique_urls'],
            duplicate_urls=url_analysis['duplicate_urls'],
            total_duplicates=url_analysis['total_duplicates'],
            duplicate_content_groups=content_analysis['duplicate_content_groups'],
            total_content_duplicates=content_analysis['total_content_duplicates'],
            efficiency_percent=efficiency,
            recommendations=results['recommendations'],
            analysis_timestamp=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Duplicate analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Duplicate analysis failed: {str(e)}")

@app.post("/duplicates/cleanup", response_model=CleanupResponse)
async def cleanup_duplicates(request: CleanupRequest):
    """Trigger manual duplicate cleanup."""
    try:
        # Import here to avoid circular imports
        import sys
        import os

        # Add the project root to Python path
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        deduplication_path = os.path.join(project_root, 'deduplication')
        if deduplication_path not in sys.path:
            sys.path.insert(0, deduplication_path)

        from cleanup_duplicates import DuplicateCleanup

        cleanup = DuplicateCleanup(dry_run=request.dry_run)
        results = cleanup.run_cleanup(
            cleanup_types=request.cleanup_types,
            strategy=request.strategy,
            similarity_threshold=request.similarity_threshold
        )

        return CleanupResponse(
            cleanup_types=request.cleanup_types,
            strategy=request.strategy,
            dry_run=request.dry_run,
            documents_processed=results['processed'],
            url_duplicates_removed=results['url_duplicates_removed'],
            content_duplicates_removed=results['content_duplicates_removed'],
            total_removed=results['total_removed'],
            errors=results['errors'],
            cleanup_timestamp=datetime.utcnow()
        )

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
