"""
Email module for rendering HTML templates and sending emails via SendGrid.
"""

import os
from datetime import datetime
from typing import List, Dict
import logging
from jinja2 import Environment, FileSystemLoader
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

from .config import CFG

# Configure logging
logger = logging.getLogger(__name__)

def categorize_articles(articles: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Categorize articles into sections based on simple keyword heuristics.
    
    Args:
        articles: List of article dictionaries with summaries
        
    Returns:
        Dictionary mapping category names to lists of articles
    """
    categories = {
        "Chips & Hardware": [],
        "Policy & Regulation": [],
        "Big Models & Platforms": [],
        "General Tech/AI": []
    }
    
    # Keywords for categorization
    chip_keywords = ["chip", "gpu", "cpu", "processor", "hardware", "nvidia", "amd", "intel", "semiconductor"]
    policy_keywords = ["regulation", "policy", "law", "government", "fcc", "ftc", "congress", "senate", "legislation"]
    big_model_keywords = ["gpt", "llm", "openai", "anthropic", "google", "meta", "microsoft", "large language model", "foundation model"]
    
    for article in articles:
        title_lower = article.get("title", "").lower()
        summary_lower = article.get("summary", "").lower()
        text_to_check = title_lower + " " + summary_lower
        
        categorized = False
        
        # Check for chip/hardware keywords
        if any(keyword in text_to_check for keyword in chip_keywords):
            categories["Chips & Hardware"].append(article)
            categorized = True
        
        # Check for policy/regulation keywords
        elif any(keyword in text_to_check for keyword in policy_keywords):
            categories["Policy & Regulation"].append(article)
            categorized = True
        
        # Check for big model/platform keywords
        elif any(keyword in text_to_check for keyword in big_model_keywords):
            categories["Big Models & Platforms"].append(article)
            categorized = True
        
        # Default to general tech/AI
        if not categorized:
            categories["General Tech/AI"].append(article)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}

def render_email_html(articles: List[Dict], date_str: str) -> str:
    """
    Render the email HTML template with articles and date.
    
    Args:
        articles: List of article dictionaries with summaries
        date_str: Formatted date string
        
    Returns:
        Rendered HTML string
    """
    # Get template directory
    template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("email.html")
    
    # Categorize articles
    sections = categorize_articles(articles)
    
    # Render template
    html = template.render(
        date_str=date_str,
        count=len(articles),
        sections=sections
    )
    
    return html

def send_email(html: str, subject: str = "Your Daily AI News Brief") -> bool:
    """
    Send email via SendGrid.
    
    Args:
        html: HTML content to send
        subject: Email subject line
        
    Returns:
        True if email sent successfully, False otherwise
    """
    if not CFG.SENDGRID_API_KEY:
        logger.error("No SendGrid API key configured")
        return False
    
    if not CFG.EMAIL_TO or not CFG.EMAIL_FROM:
        logger.error("Email addresses not configured")
        return False
    
    try:
        # Create SendGrid message
        message = Mail(
            from_email=Email(CFG.EMAIL_FROM),
            to_emails=To(CFG.EMAIL_TO),
            subject=subject,
            html_content=Content("text/html", html)
        )
        
        # Send email with error handling
        try:
            sg = SendGridAPIClient(api_key=CFG.SENDGRID_API_KEY)
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully to {CFG.EMAIL_TO}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.body}")
                return False
                
        except TypeError as e:
            if "proxies" in str(e):
                # Handle SendGrid version compatibility issue
                logger.warning("SendGrid version compatibility issue detected, trying alternative approach")
                import requests
                headers = {
                    'Authorization': f'Bearer {CFG.SENDGRID_API_KEY}',
                    'Content-Type': 'application/json'
                }
                data = {
                    'personalizations': [{'to': [{'email': CFG.EMAIL_TO}]}],
                    'from': {'email': CFG.EMAIL_FROM},
                    'subject': subject,
                    'content': [{'type': 'text/html', 'value': html}]
                }
                response = requests.post('https://api.sendgrid.com/v3/mail/send', headers=headers, json=data)
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Email sent successfully to {CFG.EMAIL_TO}")
                    return True
                else:
                    logger.error(f"Failed to send email: {response.status_code} - {response.text}")
                    return False
            else:
                raise e
            
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False
