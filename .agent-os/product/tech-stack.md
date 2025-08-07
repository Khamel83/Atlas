# Technical Stack

> Last Updated: 2025-08-02
> Version: 1.0.0

## Application Framework

- **Framework:** FastAPI
- **Version:** 0.116.1

## Database

- **Primary Database:** SQLAlchemy ORM with APScheduler backend
- **Version:** SQLAlchemy 2.0.41, APScheduler 3.11.0
- **Storage:** Local filesystem with JSON and JSONL files for content

## JavaScript

- **Framework:** Vanilla JavaScript with Jinja2 templates
- **Version:** Jinja2 3.1.6

## CSS Framework

- **Framework:** Custom CSS with FastAPI static serving

## UI Component Library

- **Library:** Rich terminal interface
- **Version:** rich 14.0.0

## Fonts Provider

- **Provider:** System fonts

## Icon Library

- **Library:** Custom icons

## Application Hosting

- **Hosting:** Self-hosted (Raspberry Pi preferred)

## Database Hosting

- **Hosting:** Local filesystem

## Asset Hosting

- **Hosting:** FastAPI static files

## Deployment Solution

- **Solution:** Systemd services for production deployment

## Code Repository URL

- **Repository:** Local development

## Content Processing Stack

- **Web Scraping:** Playwright 1.53.0, requests 2.32.4, playwright-stealth 2.0.0
- **HTML Processing:** BeautifulSoup4 4.13.4, lxml 6.0.0, readability-lxml 0.8.4.1
- **Content Extraction:** html2text 2025.4.15, markdownify 1.1.0
- **YouTube Processing:** pytube 15.0.0, youtube-transcript-api 1.1.1
- **Podcast Processing:** feedparser 6.0.11

## AI and LLM Integration

- **LLM Routing:** litellm 1.74.6
- **OpenAI API:** openai 1.97.0
- **Model Management:** tiktoken 0.9.0, tokenizers 0.21.2
- **AI Processing:** huggingface-hub 0.33.4

## Development Tools

- **Testing:** pytest 8.4.1, pytest-mock 3.14.1, responses 0.25.7
- **Code Quality:** black, isort, mypy
- **Type Checking:** typing_extensions 4.14.1, annotated-types 0.7.0
- **Progress Tracking:** tqdm 4.67.1

## Infrastructure

- **Job Scheduling:** APScheduler 3.11.0
- **ASGI Server:** uvicorn 0.35.0
- **Configuration:** python-dotenv 1.1.1, PyYAML 6.0.2
- **Validation:** pydantic 2.11.7, jsonschema 4.25.0

## Security & Privacy

- **Data Encryption:** Built-in Python cryptography
- **Local Storage:** All data stored locally, no cloud dependencies
- **API Security:** Rate limiting, authentication tokens
- **Privacy First:** No external data transmission except for configured API calls
