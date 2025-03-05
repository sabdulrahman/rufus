import os
import json
import asyncio
from rufus import RufusClient
from dotenv import load_dotenv

async def main():
    # Load environment variables from .env file
    load_dotenv()

    # Get API key from environment, preferring RUFUS_API_KEY
    api_key = os.getenv('RUFUS_API_KEY')
    
    # Fall back to OPENAI_API_KEY if RUFUS_API_KEY is not set
    if not api_key:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            print("Note: Using OPENAI_API_KEY as fallback. Consider setting RUFUS_API_KEY instead.")
    
    if not api_key:
        raise ValueError("Please set the RUFUS_API_KEY environment variable")
    
    # Initialize the Rufus client
    client = RufusClient(api_key=api_key)
    
    # Get user input for configuration
    use_browser = input("Use headless browser for JavaScript rendering? (y/n, default: y): ").lower() != 'n'
    browser_type = "playwright"
    if use_browser:
        browser_type = input("Browser type (playwright/selenium, default: playwright): ").lower() or "playwright"
    
    # Custom configuration with browser support
    custom_config = {
        "stay_in_domain": True,
        "crawl_delay": 1.5,  # Be polite
        "max_concurrent_requests": 3,
        "relevance_threshold": 0.3,
        "use_llm_for_synthesis": True,
        
        # Browser configuration
        "use_browser": use_browser,
        "browser_type": browser_type,
        "browser_wait_time": 2,  # Wait 2 seconds after page load
        "playwright_wait_until": "networkidle"  # Wait until network is idle
    }
    client.set_config(custom_config)
    
    # Get user input for scraping
    url = input("Enter the URL to scrape: ")
    instructions = input("Enter your instructions: ")
    max_pages = int(input("Maximum number of pages to crawl (default: 5): ") or "5")
    
    print(f"\nScraping {url} with {'headless browser' if use_browser else 'standard HTTP requests'}")
    print(f"Instructions: '{instructions}'")
    print(f"Please wait, this may take a few minutes...\n")
    
    # Scrape the website asynchronously (required for browser support)
    documents = await client.scrape(url, instructions, max_pages=max_pages, output_format="json")
    
    # Print summary
    print("\n" + await client.get_summary(documents) + "\n")
    
    # Save the documents
    output_file = "rufus_output.json"
    with open(output_file, "w") as f:
        json.dump(documents, f, indent=2)
    
    print(f"Saved {len(documents)} documents to {output_file}")
    
    # Ask if the user wants to view a document
    if documents and input("\nWould you like to view a document? (y/n): ").lower() == 'y':
        doc_idx = 0
        print("\n" + "="*50)
        print(f"Document Title: {documents[doc_idx]['title']}")
        print(f"Sources: {documents[doc_idx]['sources']}")
        print(f"JavaScript Rendered: {documents[doc_idx]['metadata'].get('rendered', False)}")
        print("="*50 + "\n")
        
        if isinstance(documents[doc_idx]['content'], list):
            print(documents[doc_idx]['content'][0]['content']['text'][:500] + "...\n")
        else:
            print(json.dumps(documents[doc_idx]['content'], indent=2)[:500] + "...\n")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())