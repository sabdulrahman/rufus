import logging
import json
import csv
import io
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
import os

from ..utils.error import RufusError, handle_error

class DocumentSynthesizer:
    """
    Document synthesizer for organizing extracted content into structured documents.
    """    
    def __init__(self, config: Any):
        """
        Initialize the document synthesizer.
        
        Args:
            config: Configuration settings
        """
        self.config = config
        self.logger = logging.getLogger("rufus.synthesizer")
        # Initialize the LLM client if needed for summarization
        if self.config.get('use_llm_for_synthesis', True):

            load_dotenv()
            
            self.llm_provider = self.config.get('llm_provider', 'openai')
            self.api_key = os.getenv('RUFUS_API_KEY')
            
            if self.llm_provider == 'openai':
                if not self.api_key:
                    self.logger.warning("RUFUS_API_KEY not found. Checking for OPENAI_API_KEY as fallback.")
                    self.api_key = os.getenv('OPENAI_API_KEY')
                    
                if not self.api_key:
                    self.logger.warning("No API key found in environment variables. Synthesis features may not work.")
                
                self.model = self.config.get('openai_model', 'gpt-4o-mini')
            else:
                raise RufusError(f"Unsupported LLM provider for synthesis: {self.llm_provider}")
    
    @handle_error
    def synthesize(self, analyzed_content: List[Dict[str, Any]], output_format: str = "json") -> List[Dict[str, Any]]:
        """
        Synthesize analyzed content into structured documents.
        Args:
            analyzed_content: Content that has been analyzed for relevance
            output_format: Format of the output documents ('json', 'text', 'csv')
        Returns:
            List of structured documents
        """
        self.logger.info(f"Synthesizing {len(analyzed_content)} pages into documents")
        
        # Group content by domain or topic if configured
        if self.config.get('group_by_domain', False):
            grouped_content = self._group_by_domain(analyzed_content)
        elif self.config.get('group_by_topic', False):
            grouped_content = self._group_by_topic(analyzed_content)
        else:
            # Each page becomes its own document
            grouped_content = {f"doc_{i}": [page] for i, page in enumerate(analyzed_content)}
        
        # Synthesize each group into a document
        documents = []
        
        for group_id, pages in grouped_content.items():
            document = self._create_document(group_id, pages, output_format)
            documents.append(document)
        
        # Sort documents by relevance if available
        if all('metadata' in doc and 'relevance_score' in doc['metadata'] for doc in documents):
            documents.sort(key=lambda x: x['metadata']['relevance_score'], reverse=True)
        
        self.logger.info(f"Synthesized {len(documents)} documents")
        return documents
    
    def _create_document(self, group_id: str, pages: List[Dict[str, Any]], output_format: str) -> Dict[str, Any]:
        """
        Create a document from a group of pages.
        Args:
            group_id: Identifier for the group
            pages: List of pages in the group
            output_format: Format of the output document
        Returns:
            Structured document
        """
        if self.config.get('use_llm_for_synthesis', True) and len(pages) > 1:
            document = self._synthesize_with_llm(group_id, pages)
        else:
            document = self._synthesize_without_llm(group_id, pages)
        if output_format == "json":
            document['content'] = self._format_as_json(document['content'])
        elif output_format == "text":
            document['content'] = self._format_as_text(document['content'])
        elif output_format == "csv":
            document['content'] = self._format_as_csv(document['content'])
        else:
            raise RufusError(f"Unsupported output format: {output_format}")
        
        return document
    
    def _synthesize_without_llm(self, group_id: str, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synthesize pages into a document without using an LLM.
        Args:
            group_id: Identifier for the group
            pages: List of pages in the group
        Returns:
            Structured document
        """
        urls = [page['url'] for page in pages]
        titles = [page['title'] for page in pages]
        
        # Calculate overall relevance score if available
        relevance_scores = [
            page['metadata'].get('relevance', {}).get('score', 0)
            for page in pages if 'metadata' in page and 'relevance' in page['metadata']
        ]
        
        overall_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else None
        combined_content = []
        
        for page in pages:
            page_content = page['content']
            
            # Use filtered text if available, otherwise use full text
            text = page_content.get('filtered_text', page_content.get('text', ''))
            
            # Add page information
            section = {
                'title': page['title'],
                'url': page['url'],
                'content': {
                    'headings': page_content.get('headings', {}),
                    'paragraphs': page_content.get('paragraphs', []),
                    'lists': page_content.get('lists', []),
                    'tables': page_content.get('tables', []),
                    'text': text
                }
            }
            
            combined_content.append(section)
        
        # Create the document
        document = {
            'id': group_id,
            'title': titles[0] if len(pages) == 1 else f"Synthesized Document: {group_id}",
            'sources': urls,
            'content': combined_content,
            'metadata': {
                'num_pages': len(pages),
                'relevance_score': overall_relevance
            }
        }
        
        return document
    
    def _synthesize_with_llm(self, group_id: str, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Synthesize pages into a document using an LLM to organize and summarize content.
        Args:
            group_id: Identifier for the group
            pages: List of pages in the group
        Returns:
            Structured document
        """
        # Extract relevant information from pages
        urls = [page['url'] for page in pages]
        titles = [page['title'] for page in pages]
        
        # Calculate overall relevance score if available
        relevance_scores = [
            page['metadata'].get('relevance', {}).get('score', 0)
            for page in pages if 'metadata' in page and 'relevance' in page['metadata']
        ]
        
        overall_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else None
        
        # Prepare content for LLM synthesis
        content_for_synthesis = []
        
        for i, page in enumerate(pages):
            page_content = page['content']
            
            # Use filtered text if available, otherwise use full text
            text = page_content.get('filtered_text', page_content.get('text', ''))
            
            # Truncate if too long
            max_chars = self.config.get('max_synthesis_chars_per_page', 3000)
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
            
            content_for_synthesis.append(f"--- PAGE {i+1}: {page['title']} ({page['url']}) ---\n{text}")
        
        # Join content with separators
        all_content = "\n\n".join(content_for_synthesis)
        
        # Generate synthesized content using LLM
        synthesized_content = self._generate_synthesis(all_content)
        
        # Create the document
        document = {
            'id': group_id,
            'title': "Synthesized Document: " + group_id,
            'sources': urls,
            'content': {
                'synthesized': synthesized_content,
                'original_pages': [
                    {
                        'title': page['title'],
                        'url': page['url'],
                        'content': {
                            'text': page['content'].get('filtered_text', page['content'].get('text', ''))
                        }
                    }
                    for page in pages
                ]
            },
            'metadata': {
                'num_pages': len(pages),
                'relevance_score': overall_relevance
            }
        }
        
        return document
    
    def _generate_synthesis(self, content: str) -> Dict[str, Any]:
        """
        Generate a synthesized document from content using an LLM.
        
        Args:
            content: Content to synthesize
            
        Returns:
            Synthesized content structure
        """
        prompt = f"""
        You are an AI assistant that synthesizes web content into structured, coherent documents.
        
        CONTENT FROM MULTIPLE WEB PAGES:
        {content}
        
        TASK:
        1. Synthesize this content into a coherent, well-structured document.
        2. Organize the information logically with headings and sections.
        3. Remove redundant information.
        4. Provide your response in JSON format with the following structure:
        {{
            "title": "An informative title for the synthesized document",
            "summary": "A concise summary of the key information",
            "sections": [
                {{
                    "heading": "Section heading",
                    "content": "Section content..."
                }},
                ...
            ],
            "key_points": ["Key point 1", "Key point 2", ...]
        }}
        """
        
        try:
            if self.llm_provider == 'openai':
                client = OpenAI(api_key=self.api_key) if self.api_key else OpenAI()
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a content synthesis assistant that creates structured documents from web content."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                content = response.choices[0].message.content
            
            # Extract the JSON response
            try:
                # Find JSON within the response
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_content = content[json_start:json_end]
                    result = json.loads(json_content)
                    return result
                else:
                    self.logger.warning("Could not find JSON in LLM synthesis response")
                    return {"error": "Failed to synthesize content"}
                    
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.error(f"Error parsing LLM synthesis response: {str(e)}")
                return {"error": f"Failed to synthesize content: {str(e)}"}
                
        except Exception as e:
            self.logger.error(f"Error calling LLM API for synthesis: {str(e)}")
            return {"error": f"Failed to synthesize content: {str(e)}"}
    
    def _group_by_domain(self, pages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group pages by domain.
        Args:
            pages: List of pages to group
        Returns:
            Dictionary mapping domain to list of pages
        """
        grouped = {}
        
        for page in pages:
            url = page['url']
            domain = url.split('/')[2]  # Extract domain from URL
            
            if domain not in grouped:
                grouped[domain] = []
                
            grouped[domain].append(page)
            
        return grouped
    
    def _group_by_topic(self, pages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group pages by topic using content similarity.
        This is a simplified implementation and could be enhanced with more sophisticated clustering.
        Args:
            pages: List of pages to group
        Returns:
            Dictionary mapping topic ID to list of pages
        """
        # For simplicity, just group by the first word of the title
        grouped = {}
        
        for page in pages:
            title = page['title']
            first_word = title.split()[0] if title and title.split() else 'untitled'
            
            topic_id = f"topic_{first_word.lower()}"
            
            if topic_id not in grouped:
                grouped[topic_id] = []
                
            grouped[topic_id].append(page)
            
        return grouped
    
    def _format_as_json(self, content: Any) -> Dict[str, Any]:
        """
        Format document content as JSON.
        Args:
            content: Document content
        Returns:
            JSON-formatted content
        """
        return content
    
    def _format_as_text(self, content: Any) -> str:
        """
        Format document content as plain text.
        Args:
            content: Document content
        Returns:
            Text-formatted content
        """
        if isinstance(content, list):
            # Handling a list of page content
            text_parts = []
            
            for section in content:
                text_parts.append(f"# {section['title']}")
                text_parts.append(f"Source: {section['url']}")
                text_parts.append("")
                
                # Add headings
                for heading_type, headings in section['content'].get('headings', {}).items():
                    for heading in headings:
                        text_parts.append(f"## {heading}")
                
                # Add paragraphs
                for paragraph in section['content'].get('paragraphs', []):
                    text_parts.append(paragraph)
                    text_parts.append("")
                
                # Add lists
                for list_item in section['content'].get('lists', []):
                    text_parts.append(f"### {list_item['type'].capitalize()} List:")
                    for item in list_item['items']:
                        text_parts.append(f"- {item}")
                    text_parts.append("")
                
                # Add main text if available
                if 'text' in section['content']:
                    text_parts.append(section['content']['text'])
                
                text_parts.append("\n---\n")
            
            return "\n".join(text_parts)
            
        elif isinstance(content, dict) and 'synthesized' in content:
            # Handling LLM-synthesized content
            synthesized = content['synthesized']
            text_parts = []
            
            # Add title and summary
            text_parts.append(f"# {synthesized.get('title', 'Synthesized Document')}")
            text_parts.append("")
            text_parts.append(synthesized.get('summary', ''))
            text_parts.append("")
            
            # Add sections
            for section in synthesized.get('sections', []):
                text_parts.append(f"## {section.get('heading', '')}")
                text_parts.append(section.get('content', ''))
                text_parts.append("")
            
            # Add key points
            if 'key_points' in synthesized and synthesized['key_points']:
                text_parts.append("## Key Points")
                for point in synthesized['key_points']:
                    text_parts.append(f"- {point}")
                text_parts.append("")
            
            # Add sources
            text_parts.append("## Sources")
            for page in content.get('original_pages', []):
                text_parts.append(f"- {page['title']}: {page['url']}")
            
            return "\n".join(text_parts)
            
        else:
            # Fallback for unknown content structure
            return str(content)
    
    def _format_as_csv(self, content: Any) -> str:
        """
        Format document content as CSV.
        Only works well for tabular data.
        Args:
            content: Document content
        Returns:
            CSV-formatted content
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        if isinstance(content, list):
            # Attempt to extract tabular data from pages
            for section in content:
                writer.writerow([f"# {section['title']} ({section['url']})"])
                writer.writerow([])
                
                # Write tables if available
                tables = section['content'].get('tables', [])
                for table in tables:
                    if 'headers' in table and table['headers']:
                        writer.writerow(table['headers'])
                        
                    for row in table.get('rows', []):
                        writer.writerow(row)
                        
                    writer.writerow([])
                
                # If no tables, try to create a simple key-value CSV
                if not tables:
                    writer.writerow(['Heading', 'Content'])
                    
                    # Add headings and their content
                    for heading_type, headings in section['content'].get('headings', {}).items():
                        for heading in headings:
                            writer.writerow([heading, ''])
                    
                    # Add paragraphs
                    for paragraph in section['content'].get('paragraphs', []):
                        writer.writerow(['Paragraph', paragraph[:100] + '...' if len(paragraph) > 100 else paragraph])
                    
                    writer.writerow([])
        
        elif isinstance(content, dict) and 'synthesized' in content:
            # Handle synthesized content
            synthesized = content['synthesized']
            
            writer.writerow(['# ' + synthesized.get('title', 'Synthesized Document')])
            writer.writerow(['Summary', synthesized.get('summary', '')])
            writer.writerow([])
            
            writer.writerow(['Section', 'Content'])
            for section in synthesized.get('sections', []):
                heading = section.get('heading', '')
                content_text = section.get('content', '')
                writer.writerow([heading, content_text[:100] + '...' if len(content_text) > 100 else content_text])
            
            writer.writerow([])
            writer.writerow(['Key Points'])
            for point in synthesized.get('key_points', []):
                writer.writerow(['', point])
                
            writer.writerow([])
            writer.writerow(['Sources'])
            for page in content.get('original_pages', []):
                writer.writerow(['', f"{page['title']}: {page['url']}"])
        
        return output.getvalue()
    
    @handle_error
    def generate_summary(self, documents: List[Dict[str, Any]]) -> str:
        """
        Generate a summary of the extracted documents.
        Args:
            documents: Documents to summarize
        Returns:
            A summary of the documents
        """
        if not documents:
            return "No documents found."
        
        # Collect information for summary
        num_documents = len(documents)
        total_pages = sum(doc['metadata'].get('num_pages', 1) for doc in documents)
        
        # Extract document titles
        titles = [doc.get('title', f"Document {i+1}") for i, doc in enumerate(documents)]
        
        # Generate summary text
        summary = [
            f"Found {num_documents} documents across {total_pages} pages.",
            "",
            "Documents:",
        ]
        
        for i, title in enumerate(titles):
            summary.append(f"{i+1}. {title}")
        
        return "\n".join(summary)   