"""
Configuration management for the daily news analyst.
Loads environment variables and provides typed configuration.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class with typed environment variables."""
    
    def __init__(self):
        # Data sources
        self.NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', '')
        self.NYT_API_KEY = os.getenv('NYT_API_KEY', '')
        self.APPROVED_SOURCES = self._parse_approved_sources()
        
        # LLM (OpenAI)
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
        self.OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        
        # Email
        self.SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
        self.EMAIL_TO = os.getenv('EMAIL_TO', '')
        self.EMAIL_FROM = os.getenv('EMAIL_FROM', '')
        self.TIMEZONE = os.getenv('TIMEZONE', 'America/Chicago')
        
        # Behavior
        self.MAX_ARTICLES = int(os.getenv('MAX_ARTICLES', '5'))
        self.MIN_CHARS_PER_ARTICLE = int(os.getenv('MIN_CHARS_PER_ARTICLE', '500'))
    
    def _parse_approved_sources(self) -> List[str]:
        """Parse approved sources from comma-separated string."""
        sources_str = os.getenv('APPROVED_SOURCES', '')
        if not sources_str:
            return []
        return [s.strip() for s in sources_str.split(',') if s.strip()]
    
    def validate(self) -> bool:
        """Validate that required configuration is present."""
        required_fields = [
            'NEWSAPI_KEY',
            'OPENAI_API_KEY', 
            'SENDGRID_API_KEY',
            'EMAIL_TO',
            'EMAIL_FROM'
        ]
        
        missing = []
        for field in required_fields:
            if not getattr(self, field):
                missing.append(field)
        
        if missing:
            print(f"Missing required configuration: {', '.join(missing)}")
            return False
        
        return True

# Global configuration instance
CFG = Config()
