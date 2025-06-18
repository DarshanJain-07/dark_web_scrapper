"""
Configuration settings for the Dark Web Scraper API.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenSearch configuration
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_scheme: str = "https"
    opensearch_user: str = ""
    opensearch_password: str = ""
    opensearch_index: str = "darkweb-content"
    opensearch_verify_certs: bool = False  # Set to False for self-signed certs
    opensearch_ssl_show_warn: bool = False
    
    # API configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = False
    
    # Pagination defaults
    default_page_size: int = 20
    max_page_size: int = 100
    
    # Search configuration
    search_timeout: int = 30  # seconds
    max_search_results: int = 1000
    
    class Config:
        env_file = ".env"
        env_prefix = ""
        case_sensitive = False
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Load OpenSearch credentials from environment if available
        if not self.opensearch_user:
            self.opensearch_user = os.getenv("OPENSEARCH_SCRAPER_USER", "")
        if not self.opensearch_password:
            self.opensearch_password = os.getenv("OPENSEARCH_SCRAPER_PASSWORD", "")
        if not self.opensearch_index:
            self.opensearch_index = os.getenv("OPENSEARCH_INDEX", "darkweb-content")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
