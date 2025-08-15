"""
Article summarization module using OpenAI's Chat Completions API.
Generates faithful, factual summaries with proper citations.
"""

import openai
from typing import List, Dict
import logging
import time

from .config import CFG

# Configure logging
logger = logging.getLogger(__name__)

def create_summary_prompt(article: Dict) -> str:
    """
    Create a prompt for summarizing a single article.
    
    Args:
        article: Article dictionary with title, source, published_at, url, and fulltext
        
    Returns:
        Formatted prompt string
    """
    # Format the date
    date_str = "Unknown date"
    if article.get("published_at"):
        date_str = article["published_at"].strftime("%B %d, %Y")
    
    # Truncate fulltext to ~8k characters to stay within token limits
    fulltext = article.get("fulltext", "")
    if len(fulltext) > 8000:
        fulltext = fulltext[:8000] + "..."
    
    prompt = f"""Please summarize and analyze the following article:

TITLE: {article.get('title', 'No title')}
SOURCE: {article.get('source', 'Unknown source')}
DATE: {date_str}
URL: {article.get('url', 'No URL')}

FULL TEXT:
{fulltext}

Please provide a summary and analysis that:
- Contains 3-4 bullet points of core facts
- Includes 1-2 sentences of analysis on significance/implications
- Links to the original source using the provided URL
- Keeps analysis balanced and fact-based
- Targets 120-160 words total
- Includes a citation at the end: [Source: {article.get('source', 'Unknown')}]

Summary and Analysis:"""
    
    return prompt

def summarize_articles(items: List[Dict]) -> List[str]:
    """
    Summarize a list of articles using OpenAI.
    
    Args:
        items: List of article dictionaries with fulltext
        
    Returns:
        List of summary strings in the same order as input
    """
    if not CFG.OPENAI_API_KEY:
        logger.error("No OpenAI API key configured")
        return []
    
    # Configure OpenAI client with error handling
    try:
        client = openai.OpenAI(api_key=CFG.OPENAI_API_KEY)
    except TypeError as e:
        if "proxies" in str(e):
            # Handle OpenAI client compatibility issue
            logger.warning("OpenAI client compatibility issue detected, trying alternative approach")
            import httpx
            client = openai.OpenAI(
                api_key=CFG.OPENAI_API_KEY,
                http_client=httpx.Client()
            )
        else:
            raise e
    
    summaries = []
    
    for i, article in enumerate(items):
        try:
            logger.info(f"Summarizing article {i+1}/{len(items)}: {article.get('title', 'No title')[:50]}...")
            
            prompt = create_summary_prompt(article)
            
            response = client.chat.completions.create(
                model=CFG.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You write faithful, concise news summaries with analysis and citations.
- Summarize core facts in 3-4 bullets.
- Provide 1-2 sentences of analysis on the significance or implications.
- Link to the original source using the provided URL; do not invent sources.
- Keep analysis balanced and fact-based.
- Target 120-160 words per article."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            summary = response.choices[0].message.content.strip()
            summaries.append(summary)
            
            # Rate limiting - small delay between requests
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error summarizing article {i+1}: {e}")
            # Add a fallback summary
            fallback = f"Error generating summary for: {article.get('title', 'Unknown title')} [Source: {article.get('source', 'Unknown')}]"
            summaries.append(fallback)
    
    logger.info(f"Generated {len(summaries)} summaries")
    return summaries
