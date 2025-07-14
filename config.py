"""Configuration management for WSJ Cartoonizer"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class Config:
    """Centralized configuration management"""
    
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # API Keys
        self.google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
        self.google_search_engine_id: Optional[str] = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.replicate_api_token: Optional[str] = os.getenv("REPLICATE_API_TOKEN")
        
        # Paths
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
        
        # Network settings
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        
        # Search settings
        self.max_search_results = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
        
        # Background removal settings
        self.enable_background_removal = os.getenv("ENABLE_BACKGROUND_REMOVAL", "false").lower() == "true"
        self.background_removal_tolerance = int(os.getenv("BACKGROUND_REMOVAL_TOLERANCE", "30"))
        self.background_removal_edge_smoothing = os.getenv("BACKGROUND_REMOVAL_EDGE_SMOOTHING", "true").lower() == "true"
        
        # Debug settings
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
    
    def validate(self):
        """Validate required configuration"""
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        if not self.google_search_engine_id:
            raise ValueError("GOOGLE_SEARCH_ENGINE_ID environment variable is required")
        
        if not self.replicate_api_token:
            raise ValueError("REPLICATE_API_TOKEN environment variable is required")


# Global config instance
config = Config()