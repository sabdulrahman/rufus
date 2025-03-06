# Rufus: Intelligent Web Data Extraction for LLMs

Rufus is an AI-powered tool designed to crawl websites intelligently based on user-defined prompts, extracting and synthesizing data into structured documents for use in Retrieval-Augmented Generation (RAG) systems.

## Features

- **Intelligent Web Crawling**: Crawl websites based on user-defined instructions, handling links, nested pages, and complex web structures.
- **Selective Content Extraction**: Extract only the content that is relevant to the user's prompt.
- **Document Synthesis**: Synthesize extracted content into structured documents ready for RAG systems.
- **Error Handling**: Robust error handling for inaccessible pages or changing website structures.
- **Flexible Output Formats**: Support for JSON, text, and CSV output formats.
- **Asynchronous Crawling**: High-performance crawling with configurable concurrency.

## Installation

```bash
pip install rufus
```

## Quick Start

```python
from rufus import RufusClient
import os

# Get API key
api_key = os.getenv('RUFUS_API_KEY')
client = RufusClient(api_key=api_key)

# Scrape a website with specific instructions
instructions = "Information on Mars"
documents = client.scrape("https://science.nasa.gov/mars/", instructions, max_pages=10, depth=2)

# Print summary of found documents
print(client.get_summary(documents))

# Save documents for use in a RAG system
with open("documents.json", "w") as f:
    json.dump(documents, f, indent=2)
```

## Configuration

Rufus can be configured with custom settings:

```python
custom_config = {
    "stay_in_domain": True,
    "max_concurrent_requests": 10,
    "relevance_threshold": 0.5,
    "use_llm_for_synthesis": True,
    "group_by_topic": True
}

client.set_config(custom_config)
```

## Architecture

Rufus consists of three main components:

1. **Crawler**: Responsible for navigating websites and extracting HTML content.
2. **Content Analyzer**: Uses LLMs to determine which content is relevant to the user's prompt.
3. **Document Synthesizer**: Organizes extracted content into structured documents.

## API Reference

### `RufusClient`

The main client for interacting with Rufus.

#### `__init__(api_key=None, config=None)`

Initialize the Rufus client.

- `api_key`: API key for accessing LLM services
- `config`: Optional configuration dictionary with custom settings

#### `scrape(url, instructions=None, max_pages=10, depth=2, output_format="json")`

Scrape a website based on the given instructions and return structured documents.

- `url`: The starting URL to scrape
- `instructions`: Instructions for what kind of information to extract
- `max_pages`: Maximum number of pages to crawl
- `depth`: Maximum depth of nested links to follow
- `output_format`: Format of the output documents ('json', 'text', 'csv')

#### `get_summary(documents)`

Generate a summary of the extracted documents.

- `documents`: The documents to summarize

#### `set_config(config)`

Update the configuration settings.

- `config`: New configuration settings

## Headless Browser Integration

For JavaScript-heavy websites, Rufus supports headless browsers:

```python
import nest_asyncio
import asyncio
import json
import os
from rufus import RufusClient

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Set up the API key and client
api_key = os.getenv('RUFUS_API_KEY')
client = RufusClient(api_key=api_key)

# Define an async function for our scraping
async def run_scraper():
    instructions = "Information on Mars"
    documents = await client.scrape("https://science.nasa.gov/mars/", instructions, max_pages=2, depth=2)
    return documents

# Run the async function using the current event loop
documents = asyncio.get_event_loop().run_until_complete(run_scraper())

# Now we can work with the documents
print(f"Found {len(documents)} documents")

with open("documents.json", "w") as f:
    json.dump(documents, f, indent=2)
```
## Requirements

- Python 3.8+
- Beautiful Soup 4
- Requests
- aiohttp (for asynchronous crawling)
- OpenAI API key (or compatible LLM provider)
- playwright
- selenium
## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
