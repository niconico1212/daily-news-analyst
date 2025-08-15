"""
Main CLI module for the daily news analyst.
Orchestrates the entire pipeline from news gathering to email sending.
"""

import argparse
import logging
from datetime import datetime
from typing import List, Dict
import sys

from .config import CFG
from .ingest import (
    fetch_newsapi_articles,
    fetch_nyt_articles,
    fetch_rss, 
    normalize_and_dedupe, 
    enrich_with_text,
    DEFAULT_RSS_FEEDS
)
from .summarize import summarize_articles
from .emailer import render_email_html, send_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def gather_articles(query: str, rss_only: bool = False) -> List[Dict]:
    """
    Gather articles from NewsAPI, NYT API, and RSS feeds.
    
    Args:
        query: Search query for NewsAPI and NYT
        rss_only: If True, only fetch from RSS feeds
        
    Returns:
        List of article dictionaries
    """
    articles = []
    
    if not rss_only:
        logger.info(f"Fetching articles from NewsAPI with query: {query}")
        newsapi_articles = fetch_newsapi_articles(query)
        articles.extend(newsapi_articles)
        
        logger.info(f"Fetching articles from NYT API with query: {query}")
        nyt_articles = fetch_nyt_articles(query)
        articles.extend(nyt_articles)
    
    logger.info("Fetching articles from RSS feeds")
    rss_articles = fetch_rss(DEFAULT_RSS_FEEDS)
    articles.extend(rss_articles)
    
    if not articles:
        logger.warning("No articles found from any source")
        return []
    
    logger.info(f"Total articles gathered: {len(articles)}")
    return articles

def process_articles(articles: List[Dict], max_articles: int, min_chars: int) -> List[Dict]:
    """
    Process articles through deduplication, enrichment, and summarization.
    
    Args:
        articles: List of raw article dictionaries
        max_articles: Maximum number of articles to process
        min_chars: Minimum characters required per article
        
    Returns:
        List of processed articles with summaries
    """
    # Deduplicate articles
    logger.info("Deduplicating articles...")
    deduplicated = normalize_and_dedupe(articles)
    
    # Sort by published date (newest first) and limit
    deduplicated.sort(
        key=lambda x: x.get("published_at") or datetime.min.replace(tzinfo=datetime.utc),
        reverse=True
    )
    
    if len(deduplicated) > max_articles:
        logger.info(f"Limiting to {max_articles} articles (from {len(deduplicated)})")
        deduplicated = deduplicated[:max_articles]
    
    # Enrich with full text
    logger.info("Enriching articles with full text...")
    enriched = enrich_with_text(deduplicated, min_chars)
    
    if not enriched:
        logger.warning("No articles with sufficient content after enrichment")
        return []
    
    # Generate summaries
    logger.info("Generating summaries...")
    summaries = summarize_articles(enriched)
    
    # Attach summaries to articles
    for article, summary in zip(enriched, summaries):
        article["summary"] = summary
    
    logger.info(f"Successfully processed {len(enriched)} articles")
    return enriched

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Daily AI News Analyst - Generate and send daily news briefs"
    )
    parser.add_argument(
        "--query", 
        default="politics OR world OR technology OR science OR business OR economy",
        help="Search query for NewsAPI (default: 'politics OR world OR technology OR science OR business OR economy')"
    )
    parser.add_argument(
        "--rss-only",
        action="store_true",
        help="Only fetch from RSS feeds, skip NewsAPI"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview HTML output instead of sending email"
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        default=CFG.MAX_ARTICLES,
        help=f"Maximum articles to process (default: {CFG.MAX_ARTICLES})"
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=CFG.MIN_CHARS_PER_ARTICLE,
        help=f"Minimum characters per article (default: {CFG.MIN_CHARS_PER_ARTICLE})"
    )
    
    args = parser.parse_args()
    
    # Validate configuration
    if not args.preview and not CFG.validate():
        logger.error("Configuration validation failed")
        sys.exit(1)
    
    try:
        # Gather articles
        articles = gather_articles(args.query, args.rss_only)
        
        if not articles:
            logger.info("No articles found. Nothing to send.")
            return
        
        # Process articles
        processed_articles = process_articles(articles, args.max_articles, args.min_chars)
        
        if not processed_articles:
            logger.info("No articles with sufficient content. Nothing to send.")
            return
        
        # Format date for email
        date_str = datetime.now().strftime("%A, %B %d, %Y")
        
        # Render email HTML
        logger.info("Rendering email HTML...")
        html = render_email_html(processed_articles, date_str)
        
        if args.preview:
            # Print HTML for preview
            print("\n" + "="*50)
            print("EMAIL PREVIEW")
            print("="*50)
            print(html)
            print("="*50)
        else:
            # Send email
            logger.info("Sending email...")
            subject = f"Daily News Brief - {date_str}"
            success = send_email(html, subject)
            
            if success:
                logger.info("Email sent successfully!")
            else:
                logger.error("Failed to send email")
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
