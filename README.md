# Daily News Analyst

A production-ready Python application that automatically generates and sends daily AI news briefs via email. The system ingests news from NewsAPI and RSS feeds, extracts full text content, generates faithful summaries using OpenAI, and delivers beautifully formatted HTML emails.

## Features

- **Multi-source news ingestion**: NewsAPI (primary) + RSS feeds (fallback/augment)
- **Full text extraction**: Uses trafilatura for comprehensive content extraction
- **Intelligent deduplication**: Removes duplicate articles across sources
- **AI-powered summarization**: OpenAI GPT-4o-mini for factual, citation-rich summaries
- **Categorized content**: Automatic categorization into relevant sections
- **Beautiful email templates**: Clean, responsive HTML emails
- **Automated scheduling**: GitHub Actions cron job for daily delivery
- **Production ready**: Error handling, logging, and graceful degradation

## Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd daily-news-analyst

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy example environment file
cp env.example .env

# Edit .env with your API keys and settings
nano .env
```

Required environment variables:
- `NEWSAPI_KEY`: Your NewsAPI API key
- `OPENAI_API_KEY`: Your OpenAI API key
- `SENDGRID_API_KEY`: Your SendGrid API key
- `EMAIL_TO`: Recipient email address
- `EMAIL_FROM`: Sender email address (must be verified in SendGrid)

### 3. Test Locally

```bash
# Preview the email HTML (no API calls needed)
python -m src.main --preview

# Test with RSS feeds only (no NewsAPI key required)
python -m src.main --rss-only --preview

# Send a real email (requires all API keys)
python -m src.main
```

## Usage

### Command Line Options

```bash
python -m src.main [OPTIONS]

Options:
  --query TEXT           Search query for NewsAPI (default: "AI OR artificial intelligence")
  --rss-only            Only fetch from RSS feeds, skip NewsAPI
  --preview             Preview HTML output instead of sending email
  --max-articles INT    Maximum articles to process (default: 12)
  --min-chars INT       Minimum characters per article (default: 800)
  --help                Show help message
```

### Examples

```bash
# Custom search query
python -m src.main --query "machine learning OR deep learning"

# Limit to 5 articles
python -m src.main --max-articles 5

# RSS feeds only (useful for testing)
python -m src.main --rss-only --preview

# Preview with custom settings
python -m src.main --query "AI" --max-articles 3 --preview
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEWSAPI_KEY` | NewsAPI API key | Required |
| `APPROVED_SOURCES` | Comma-separated NewsAPI source slugs | Optional |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o-mini` |
| `SENDGRID_API_KEY` | SendGrid API key | Required |
| `EMAIL_TO` | Recipient email address | Required |
| `EMAIL_FROM` | Sender email address | Required |
| `TIMEZONE` | Timezone for date formatting | `America/Chicago` |
| `MAX_ARTICLES` | Maximum articles to process | `12` |
| `MIN_CHARS_PER_ARTICLE` | Minimum characters per article | `800` |

### Adding/Replacing Sources

#### NewsAPI Sources
Add approved sources to your `.env` file:
```
APPROVED_SOURCES=the-verge,techcrunch,ars-technica,wired,engadget
```

#### RSS Feeds
Edit `src/ingest.py` to modify the `DEFAULT_RSS_FEEDS` list:
```python
DEFAULT_RSS_FEEDS = [
    "https://www.theverge.com/rss/index.xml",
    "https://techcrunch.com/feed/",
    # Add your preferred RSS feeds here
]
```

## GitHub Actions Setup

### 1. Add Repository Secrets

Go to your repository Settings → Secrets and variables → Actions, and add:

- `NEWSAPI_KEY`: Your NewsAPI API key
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: `gpt-4o-mini` (or your preferred model)
- `SENDGRID_API_KEY`: Your SendGrid API key
- `EMAIL_FROM`: Your verified sender email
- `EMAIL_TO`: Recipient email address
- `TIMEZONE`: `America/Chicago`
- `MAX_ARTICLES`: `12`
- `MIN_CHARS_PER_ARTICLE`: `800`
- `APPROVED_SOURCES`: `the-verge,techcrunch,ars-technica` (optional)

### 2. Schedule

The workflow runs automatically at **7:07 AM Chicago time** (12:07 UTC) daily. You can also trigger it manually from the Actions tab.

## Safety & Best Practices

### API Key Security
- **Never commit API keys** to version control
- Use `.env` file for local development (already in `.gitignore`)
- Use GitHub Secrets for production deployment
- Rotate keys regularly

### SendGrid Setup
1. Create a SendGrid account
2. Verify your sender domain or email address
3. Generate an API key with "Mail Send" permissions
4. Add the API key to your environment variables

### Rate Limiting
- NewsAPI: 1000 requests/day (free tier)
- OpenAI: Varies by model and plan
- The application includes built-in delays to respect rate limits

## Troubleshooting

### Common Issues

**"No NewsAPI key configured"**
- Add your NewsAPI API key to `.env` or GitHub Secrets
- Get a free key at [newsapi.org](https://newsapi.org)

**"Failed to send email"**
- Verify your SendGrid API key
- Ensure sender email is verified in SendGrid
- Check SendGrid logs for detailed error messages

**"No articles found"**
- Check your NewsAPI query syntax
- Verify RSS feed URLs are accessible
- Try `--rss-only` to test RSS feeds independently

**"OpenAI API error"**
- Verify your OpenAI API key
- Check your OpenAI account balance
- Ensure the specified model is available

### Debug Mode

Enable debug logging by modifying the logging level in any module:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Network Issues

The application handles network errors gracefully:
- Failed article extractions are skipped
- RSS feed failures don't stop the entire process
- API timeouts are handled with retries

## Architecture

```
daily-news-analyst/
├── src/
│   ├── config.py      # Configuration management
│   ├── ingest.py      # News fetching and processing
│   ├── summarize.py   # OpenAI integration
│   ├── emailer.py     # Email rendering and sending
│   └── main.py        # CLI and orchestration
├── templates/
│   └── email.html     # Email template
├── .github/workflows/
│   └── daily.yml      # GitHub Actions workflow
├── requirements.txt   # Python dependencies
├── env.example        # Environment template
└── README.md         # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the logs for error messages
3. Open an issue on GitHub with detailed information

---

**Happy news analyzing! 🤖📰**
