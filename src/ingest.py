"""
News ingestion module for fetching and processing articles from multiple sources.
Handles NewsAPI, RSS feeds, text extraction, and deduplication.
"""

import requests
import feedparser
import trafilatura
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone
from typing import List, Dict, Optional
from tqdm import tqdm
import time
import logging

from .config import CFG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default RSS feeds for general news (politics, global, tech, etc.)
DEFAULT_RSS_FEEDS = [
    "https://feeds.npr.org/1001/rss.xml",  # NPR General News
    "https://feeds.bbci.co.uk/news/rss.xml",  # BBC General News
    "https://feeds.bbci.co.uk/news/politics/rss.xml",  # BBC Politics
    "https://feeds.bbci.co.uk/news/world/rss.xml",  # BBC World News
    "https://www.theguardian.com/world/rss",  # The Guardian World
    "https://www.theguardian.com/politics/rss",  # The Guardian Politics
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",  # NYT World
    "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",  # NYT Politics
    "https://feeds.foxnews.com/foxnews/latest",  # Fox News Latest
    "https://feeds.foxnews.com/foxnews/politics",  # Fox News Politics
]

def fetch_nyt_articles(query: str) -> List[Dict]:
    """
    Fetch articles from New York Times API.
    
    Args:
        query: Search query string
        
    Returns:
        List of article dictionaries
    """
    if not CFG.NYT_API_KEY:
        logger.warning("No NYT API key configured, skipping NYT fetch")
        return []
    
    url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
    params = {
        "q": query,
        "api-key": CFG.NYT_API_KEY,
        "sort": "newest",
        "fl": "headline,web_url,source,pub_date,abstract,lead_paragraph",
        "fq": "news_desk:(Technology OR Science OR Business)",
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        articles = []
        for doc in data.get("response", {}).get("docs", []):
            # Parse published date
            published_at = None
            if doc.get("pub_date"):
                try:
                    published_at = datetime.fromisoformat(
                        doc["pub_date"].replace("Z", "+00:00")
                    )
                except ValueError:
                    published_at = datetime.now(timezone.utc)
            
            articles.append({
                "title": doc.get("headline", {}).get("main", "").strip(),
                "url": doc.get("web_url", ""),
                "source": "The New York Times",
                "published_at": published_at,
                "description": doc.get("abstract", "").strip(),
                "content": doc.get("lead_paragraph", "").strip(),
                "source_type": "nyt_api"
            })
        
        logger.info(f"Fetched {len(articles)} articles from NYT API")
        return articles
        
    except requests.RequestException as e:
        logger.error(f"Error fetching from NYT API: {e}")
        return []

def fetch_newsapi_articles(query: str) -> List[Dict]:
    """
    Fetch articles from NewsAPI with the given query.
    
    Args:
        query: Search query string
        
    Returns:
        List of article dictionaries with title, url, source, published_at, description, content
    """
    if not CFG.NEWSAPI_KEY:
        logger.warning("No NewsAPI key configured, skipping NewsAPI fetch")
        return []
    
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "apiKey": CFG.NEWSAPI_KEY,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 50,  # Get more articles for better selection
    }
    
    # Add approved sources if configured
    if CFG.APPROVED_SOURCES:
        params["sources"] = ",".join(CFG.APPROVED_SOURCES)
    else:
        # Default to major news sources if no approved sources specified
        params["sources"] = "npr,bbc-news,fox-news"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "ok":
            logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
            return []
        
        articles = []
        for article in data.get("articles", []):
            # Parse published date
            published_at = None
            if article.get("publishedAt"):
                try:
                    published_at = datetime.fromisoformat(
                        article["publishedAt"].replace("Z", "+00:00")
                    )
                except ValueError:
                    published_at = datetime.now(timezone.utc)
            
            articles.append({
                "title": article.get("title", "").strip(),
                "url": article.get("url", ""),
                "source": article.get("source", {}).get("name", "Unknown"),
                "published_at": published_at,
                "description": article.get("description", "").strip(),
                "content": article.get("content", "").strip(),
                "source_type": "newsapi"
            })
        
        logger.info(f"Fetched {len(articles)} articles from NewsAPI")
        return articles
        
    except requests.RequestException as e:
        logger.error(f"Error fetching from NewsAPI: {e}")
        return []

def fetch_rss(urls: List[str]) -> List[Dict]:
    """
    Fetch articles from RSS feeds.
    
    Args:
        urls: List of RSS feed URLs
        
    Returns:
        List of article dictionaries
    """
    articles = []
    
    for url in urls:
        try:
            logger.info(f"Fetching RSS feed: {url}")
            feed = feedparser.parse(url)
            
            for entry in feed.entries:
                # Parse published date
                published_at = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published_at = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                else:
                    published_at = datetime.now(timezone.utc)
                
                # Clean description with BeautifulSoup
                description = ""
                if hasattr(entry, 'summary'):
                    soup = BeautifulSoup(entry.summary, 'html.parser')
                    description = soup.get_text().strip()
                
                articles.append({
                    "title": getattr(entry, 'title', '').strip(),
                    "url": getattr(entry, 'link', ''),
                    "source": feed.feed.get('title', 'Unknown RSS'),
                    "published_at": published_at,
                    "description": description,
                    "content": "",  # RSS feeds don't provide full content
                    "source_type": "rss"
                })
                
        except Exception as e:
            logger.error(f"Error fetching RSS feed {url}: {e}")
            continue
    
    logger.info(f"Fetched {len(articles)} articles from RSS feeds")
    return articles

def extract_fulltext(url: str, timeout: int = 10) -> Optional[str]:
    """
    Extract full text content from a URL using trafilatura.
    
    Args:
        url: URL to extract text from
        timeout: Request timeout in seconds
        
    Returns:
        Extracted text or None if extraction failed
    """
    try:
        extracted = trafilatura.fetch_url(url, timeout=timeout)
        if extracted:
            text = trafilatura.extract(extracted, include_links=False, include_images=False)
            if text:
                return text.strip()
    except Exception as e:
        logger.debug(f"Failed to extract text from {url}: {e}")
    
    return None

def normalize_url(url: str) -> str:
    """
    Normalize URL by removing query parameters and fragments.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL
    """
    try:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        return url

def normalize_title(title: str) -> str:
    """
    Normalize title for deduplication by removing common suffixes and normalizing case.
    
    Args:
        title: Title to normalize
        
    Returns:
        Normalized title
    """
    # Remove common suffixes
    suffixes = [" - The Verge", " | TechCrunch", " | Ars Technica", " | Wired", " | Engadget"]
    normalized = title
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            break
    
    return normalized.lower().strip()

def normalize_and_dedupe(items: List[Dict]) -> List[Dict]:
    """
    Normalize and deduplicate articles by URL and title.
    Prioritize tech/science articles.
    
    Args:
        items: List of article dictionaries
        
    Returns:
        Deduplicated list of articles
    """
    seen_urls = set()
    seen_titles = set()
    deduplicated = []
    
    # Keywords to prioritize important news (politics, world events, tech, etc.)
    priority_keywords = [
        "politics", "election", "government", "president", "congress", "senate",
        "world", "global", "international", "foreign", "diplomacy", "trade",
        "technology", "science", "innovation", "AI", "artificial intelligence", 
        "climate", "economy", "business", "finance", "market", "trade",
        "breaking", "urgent", "crisis", "emergency", "important", "major"
    ]
    
    # Sort by published_at (newest first) to keep the most recent version
    items.sort(key=lambda x: x.get("published_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    
    for item in items:
        normalized_url = normalize_url(item["url"])
        normalized_title = normalize_title(item["title"])
        
        # Skip if we've seen this URL or very similar title
        if normalized_url in seen_urls:
            continue
        
        if normalized_title in seen_titles:
            continue
        
        # Add priority score for tech/science articles
        title_lower = item.get("title", "").lower()
        priority_score = sum(1 for keyword in priority_keywords if keyword in title_lower)
        item["priority_score"] = priority_score
        
        seen_urls.add(normalized_url)
        seen_titles.add(normalized_title)
        deduplicated.append(item)
    
    # Sort by priority score (highest first), then by date
    deduplicated.sort(key=lambda x: (x.get("priority_score", 0), x.get("published_at") or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    
    logger.info(f"Deduplicated {len(items)} articles to {len(deduplicated)}")
    return deduplicated

def enrich_with_text(items: List[Dict], min_chars: int = 100) -> List[Dict]:
    """
    Enrich articles with full text content, preferring existing content over extraction.
    
    Args:
        items: List of article dictionaries
        min_chars: Minimum characters required to keep an article
        
    Returns:
        List of articles with fulltext added
    """
    enriched = []
    
    for item in tqdm(items, desc="Enriching articles with full text"):
        fulltext = ""
        
        # Prefer existing content from NewsAPI or NYT API
        if item.get("content") and len(item["content"]) > min_chars:
            fulltext = item["content"]
        elif item.get("description") and len(item["description"]) > min_chars:
            fulltext = item["description"]
        else:
            # Try to extract full text as last resort
            extracted = extract_fulltext(item["url"])
            if extracted and len(extracted) > min_chars:
                fulltext = extracted
            elif item.get("description"):  # Use description even if short
                fulltext = item["description"]
        
        if fulltext:
            item["fulltext"] = fulltext
            enriched.append(item)
        else:
            logger.debug(f"Skipping article with insufficient content: {item['title']}")
        
        # Small delay to be respectful to servers
        time.sleep(0.1)
    
    logger.info(f"Enriched {len(enriched)} articles with full text")
    return enriched
