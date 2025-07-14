"""Extract author information from article URLs"""

import json
import re
from typing import Tuple, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from config import config


class AuthorExtractor:
    """Extract author names from article pages"""
    
    def __init__(self):
        self.timeout = config.request_timeout
        self.client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    def extract_author(self, url: str) -> Tuple[str, Optional[str]]:
        """Extract author name and publisher from article URL
        
        Returns:
            Tuple of (author_name, publisher)
        """
        # Validate URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(f"Invalid URL format: {url}")
        except Exception as e:
            raise ValueError(f"Invalid URL: {url}") from e
        
        # Extract publisher from domain
        publisher = self._extract_publisher(parsed.netloc)
        
        # Fetch the page
        try:
            response = self.client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Failed to fetch URL: {e.response.status_code}") from e
        except Exception as e:
            raise ValueError(f"Failed to fetch URL: {e}") from e
        
        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Try multiple extraction methods
        author_name = None
        
        # Method 1: JSON-LD structured data
        if not author_name:
            author_name = self._parse_json_ld(soup)
            if author_name and config.debug:
                print(f"[AUTHOR] Found via JSON-LD: {author_name}")
        
        # Method 2: Meta tags
        if not author_name:
            author_name = self._parse_metadata(soup)
            if author_name and config.debug:
                print(f"[AUTHOR] Found via meta tags: {author_name}")
        
        # Method 3: Byline patterns
        if not author_name:
            author_name = self._parse_byline(soup)
            if author_name and config.debug:
                print(f"[AUTHOR] Found via byline: {author_name}")
        
        if not author_name:
            raise ValueError(f"Could not extract author from {url}")
        
        # Clean and normalize author name
        author_name = self._clean_author_name(author_name)
        
        return author_name, publisher
    
    def _extract_publisher(self, domain: str) -> Optional[str]:
        """Extract publisher name from domain"""
        domain = domain.lower()
        
        # Map common domains to publisher names
        publisher_map = {
            'wsj.com': 'Wall Street Journal',
            'theatlantic.com': 'The Atlantic',
            'nytimes.com': 'New York Times',
            'washingtonpost.com': 'Washington Post',
            'cnn.com': 'CNN',
            'bbc.com': 'BBC',
            'reuters.com': 'Reuters',
            'npr.org': 'NPR',
            'forbes.com': 'Forbes',
            'bloomberg.com': 'Bloomberg',
            'wired.com': 'Wired',
            'techcrunch.com': 'TechCrunch',
            'theverge.com': 'The Verge',
            'ft.com': 'Financial Times',
            'economist.com': 'The Economist',
            'politico.com': 'Politico',
            'axios.com': 'Axios',
            'vox.com': 'Vox'
        }
        
        for domain_key, publisher_name in publisher_map.items():
            if domain_key in domain:
                return publisher_name
        
        # Fallback: extract main domain name
        domain_parts = domain.replace('www.', '').split('.')
        if len(domain_parts) >= 2:
            return domain_parts[0].title()
        
        return None
    
    def _parse_json_ld(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author from JSON-LD structured data"""
        scripts = soup.find_all("script", type="application/ld+json")
        
        for script in scripts:
            try:
                data = json.loads(script.string)
                
                # Handle single object or array
                if isinstance(data, list):
                    data = data[0] if data else {}
                
                # Check for author field
                author = data.get("author")
                if author:
                    if isinstance(author, dict):
                        return author.get("name", "")
                    elif isinstance(author, str):
                        return author
                
                # Check for NewsArticle or Article types
                if data.get("@type") in ["NewsArticle", "Article", "BlogPosting"]:
                    author = data.get("author")
                    if author:
                        if isinstance(author, dict):
                            return author.get("name", "")
                        elif isinstance(author, str):
                            return author
                
            except (json.JSONDecodeError, AttributeError):
                continue
        
        return None
    
    def _parse_metadata(self, soup: BeautifulSoup) -> Optional[str]:
        """Parse author from meta tags"""
        # Common meta tag patterns
        meta_names = [
            "author",
            "article:author",
            "dc.creator",
            "dcterms.creator",
            "twitter:creator",
            "parsely-author",
            "byl"
        ]
        
        for name in meta_names:
            # Try name attribute
            meta = soup.find("meta", attrs={"name": name})
            if meta and meta.get("content"):
                return meta["content"]
            
            # Try property attribute
            meta = soup.find("meta", attrs={"property": name})
            if meta and meta.get("content"):
                return meta["content"]
        
        return None
    
    def _parse_byline(self, soup: BeautifulSoup) -> Optional[str]:
        """Parse author from byline patterns in content"""
        # Common byline classes
        byline_classes = [
            "byline", "author", "by-line", "article-author",
            "entry-author", "post-author", "author-name",
            "by", "written-by", "article-byline"
        ]
        
        # Search by class
        for class_name in byline_classes:
            elements = soup.find_all(class_=re.compile(class_name, re.I))
            for elem in elements:
                text = elem.get_text(strip=True)
                author = self._extract_from_byline_text(text)
                if author:
                    return author
        
        # Search by common patterns in text
        patterns = [
            r"[Bb]y\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"[Aa]uthor:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"[Ww]ritten\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)"
        ]
        
        # Search in common container elements
        for tag in ["div", "span", "p", "address"]:
            elements = soup.find_all(tag)
            for elem in elements[:100]:  # Limit to first 100 elements
                text = elem.get_text(strip=True)
                for pattern in patterns:
                    match = re.search(pattern, text)
                    if match:
                        return match.group(1)
        
        return None
    
    def _extract_from_byline_text(self, text: str) -> Optional[str]:
        """Extract author name from byline text"""
        # Remove common prefixes
        text = re.sub(r"^(by|author:|written by)\s*", "", text, flags=re.I)
        
        # Remove dates and other noise
        text = re.sub(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", "", text)
        text = re.sub(r"(published|updated|posted)\s*:?\s*", "", text, flags=re.I)
        
        # Extract name pattern (capitalize words)
        match = re.match(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", text.strip())
        if match:
            return match.group(1)
        
        # If no pattern matches but text is reasonable length, return it
        text = text.strip()
        if 2 <= len(text.split()) <= 4 and len(text) < 50:
            return text
        
        return None
    
    def _clean_author_name(self, name: str) -> str:
        """Clean and normalize author name"""
        # Remove extra whitespace
        name = " ".join(name.split())
        
        # Remove common suffixes
        name = re.sub(r"\s*,?\s*(Jr\.?|Sr\.?|III|IV|PhD|MD)$", "", name, flags=re.I)
        
        # Remove email patterns
        name = re.sub(r"\s*\S+@\S+\.\S+", "", name)
        
        # Remove twitter handles
        name = re.sub(r"\s*@\w+", "", name)
        
        # Ensure proper capitalization
        words = name.split()
        normalized = []
        for word in words:
            if word.isupper() or word.islower():
                word = word.capitalize()
            normalized.append(word)
        
        return " ".join(normalized)
    
    def __del__(self):
        """Clean up HTTP client"""
        if hasattr(self, "client"):
            self.client.close()