"""
Pydantic models for API request/response validation.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


class SortField(str, Enum):
    """Available fields for sorting."""
    TIMESTAMP = "timestamp"
    URL = "url"
    RELEVANCE = "_score"


class ScrapedDocument(BaseModel):
    """Model for a scraped document."""
    id: Optional[str] = Field(None, description="Document ID")
    url: str = Field(..., description="The scraped URL")
    text_content: str = Field(..., description="Extracted text content")
    html_content: Optional[str] = Field(None, description="Raw HTML content")
    timestamp: datetime = Field(..., description="When the document was scraped")
    score: Optional[float] = Field(None, description="Search relevance score")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SearchRequest(BaseModel):
    """Model for search requests."""
    query: str = Field(..., description="Search query string")
    page: int = Field(1, ge=1, description="Page number (1-based)")
    size: int = Field(20, ge=1, le=100, description="Number of results per page")
    sort_field: SortField = Field(SortField.RELEVANCE, description="Field to sort by")
    sort_order: SortOrder = Field(SortOrder.DESC, description="Sort order")
    include_html: bool = Field(False, description="Include HTML content in results")


class SearchResponse(BaseModel):
    """Model for search response."""
    documents: List[ScrapedDocument] = Field(..., description="List of matching documents")
    total: int = Field(..., description="Total number of matching documents")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of results per page")
    total_pages: int = Field(..., description="Total number of pages")
    took: int = Field(..., description="Time taken for search in milliseconds")


class DocumentResponse(BaseModel):
    """Model for single document response."""
    document: ScrapedDocument = Field(..., description="The requested document")
    found: bool = Field(..., description="Whether the document was found")


class HealthResponse(BaseModel):
    """Model for health check response."""
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    opensearch_connected: bool = Field(..., description="OpenSearch connection status")
    error: Optional[str] = Field(None, description="Error message if unhealthy")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StatsResponse(BaseModel):
    """Model for statistics response."""
    total_documents: int = Field(..., description="Total number of scraped documents")
    unique_urls: int = Field(..., description="Number of unique URLs")
    latest_scrape: Optional[datetime] = Field(None, description="Timestamp of latest scrape")
    oldest_scrape: Optional[datetime] = Field(None, description="Timestamp of oldest scrape")
    index_size: Optional[str] = Field(None, description="Index size in human readable format")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class URLListResponse(BaseModel):
    """Model for URL list response."""
    urls: List[str] = Field(..., description="List of scraped URLs")
    total: int = Field(..., description="Total number of URLs")
    page: int = Field(..., description="Current page number")
    size: int = Field(..., description="Number of URLs per page")
    total_pages: int = Field(..., description="Total number of pages")


class ErrorResponse(BaseModel):
    """Model for error responses."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DuplicateAnalysisResponse(BaseModel):
    """Model for duplicate analysis response."""
    total_documents: int = Field(..., description="Total number of documents")
    unique_urls: int = Field(..., description="Number of unique URLs")
    duplicate_urls: int = Field(..., description="Number of URLs with duplicates")
    total_duplicates: int = Field(..., description="Total number of duplicate documents")
    duplicate_content_groups: int = Field(..., description="Number of content duplicate groups")
    total_content_duplicates: int = Field(..., description="Total content duplicates")
    efficiency_percent: float = Field(..., description="Database efficiency percentage")
    recommendations: List[str] = Field(..., description="Cleanup recommendations")
    analysis_timestamp: datetime = Field(..., description="When analysis was performed")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CleanupRequest(BaseModel):
    """Model for cleanup requests."""
    cleanup_types: List[str] = Field(["url", "content"], description="Types of cleanup to perform")
    strategy: str = Field("latest", description="Strategy for selecting documents to keep")
    similarity_threshold: float = Field(0.95, ge=0.0, le=1.0, description="Similarity threshold for content cleanup")
    dry_run: bool = Field(True, description="Whether to perform a dry run")


class CleanupResponse(BaseModel):
    """Model for cleanup response."""
    cleanup_types: List[str] = Field(..., description="Types of cleanup performed")
    strategy: str = Field(..., description="Strategy used")
    dry_run: bool = Field(..., description="Whether this was a dry run")
    documents_processed: int = Field(..., description="Number of documents processed")
    url_duplicates_removed: int = Field(..., description="URL duplicates removed")
    content_duplicates_removed: int = Field(..., description="Content duplicates removed")
    total_removed: int = Field(..., description="Total documents removed")
    errors: int = Field(..., description="Number of errors encountered")
    cleanup_timestamp: datetime = Field(..., description="When cleanup was performed")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
