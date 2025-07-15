"""Find author images using Google Custom Search API"""

from typing import Optional

import httpx

from config import config


class ImageFinder:
    """Find author photos through Google Custom Search"""
    
    def __init__(self):
        self.timeout = config.request_timeout
        self.client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
    
    def find_author_image(self, author_name: str, publisher: Optional[str] = None) -> str:
        """Find author photo using Google Custom Search
        
        Returns:
            URL of the best author image found
        """
        if config.debug:
            print(f"[IMAGE SEARCH] Searching for: {author_name}")
        
        # Build search query
        if publisher:
            query = f'"{author_name}" "{publisher}"'
        else:
            query = f'"{author_name}"'
        
        if config.debug:
            print(f"[IMAGE SEARCH] Query: {query}")
        else:
            # Always log query for Railway debugging
            print(f"[IMAGE SEARCH] Searching for: {author_name}, Query: {query}")
        
        # Search using Google Custom Search API
        params = {
            "key": config.google_api_key,
            "cx": config.google_search_engine_id,
            "q": query,
            "searchType": "image",
            "num": config.max_search_results,
            "imgSize": "large",  # Prefer larger images
            "imgType": "face"    # Focus on faces/portraits
        }
        
        # Always log API params (without exposing full API key)
        debug_params = params.copy()
        if debug_params.get("key"):
            debug_params["key"] = f"{debug_params['key'][:8]}...{debug_params['key'][-4:]}"
        print(f"[IMAGE SEARCH] API params: {debug_params}")
        
        try:
            response = self.client.get(
                "https://www.googleapis.com/customsearch/v1",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Enhanced debugging for Railway deployment issues
            if config.debug:
                total_results = len(data.get("items", []))
                print(f"[IMAGE SEARCH] Found {total_results} results")
                print(f"[IMAGE SEARCH] Response keys: {list(data.keys())}")
                if "searchInformation" in data:
                    search_info = data["searchInformation"]
                    print(f"[IMAGE SEARCH] Total results: {search_info.get('totalResults', 'unknown')}")
                    print(f"[IMAGE SEARCH] Search time: {search_info.get('searchTime', 'unknown')}")
                if "error" in data:
                    print(f"[IMAGE SEARCH] API Error: {data['error']}")
            else:
                # Always log for Railway debugging
                total_results = len(data.get("items", []))
                print(f"[IMAGE SEARCH] Found {total_results} results for '{author_name}'")
                if "error" in data:
                    print(f"[IMAGE SEARCH] API Error: {data['error']}")
                if total_results == 0 and "searchInformation" in data:
                    print(f"[IMAGE SEARCH] Google says total results: {data['searchInformation'].get('totalResults', 'unknown')}")
            
            if "items" not in data or not data["items"]:
                # Log the full response for debugging on Railway
                print(f"[IMAGE SEARCH] No items in response. Full response: {data}")
                raise ValueError("No images found for author")
            
            # Find the best image (first valid one)
            for i, result in enumerate(data["items"]):
                img_url = result.get("link")
                if not img_url:
                    continue
                
                # Basic validation
                if not self._is_valid_image_url(img_url):
                    continue
                
                # Get image dimensions if available
                image_width = int(result.get("image", {}).get("width", 0))
                image_height = int(result.get("image", {}).get("height", 0))
                
                # Skip very small images
                if image_width > 0 and image_height > 0:
                    if image_width < 200 or image_height < 200:
                        if config.debug:
                            print(f"[IMAGE SEARCH] Skipping small image: {image_width}x{image_height}")
                        continue
                
                if config.debug:
                    print(f"[IMAGE SEARCH] Selected image {i+1}: {img_url[:60]}...")
                    if image_width > 0:
                        print(f"[IMAGE SEARCH] Dimensions: {image_width}x{image_height}")
                
                return img_url
            
            raise ValueError("No valid images found for author")
            
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Google search failed: {e.response.status_code}") from e
        except Exception as e:
            raise ValueError(f"Failed to search for author image: {e}") from e
    
    def download_image(self, url: str) -> bytes:
        """Download image from URL
        
        Returns:
            Image data as bytes
        """
        try:
            if config.debug:
                print(f"[DOWNLOAD] Fetching image from: {url[:60]}...")
            
            response = self.client.get(url)
            response.raise_for_status()
            
            # Validate content type
            content_type = response.headers.get("content-type", "").lower()
            if not any(img_type in content_type for img_type in ["image/", "application/octet-stream"]):
                raise ValueError(f"Invalid content type: {content_type}")
            
            # Check size
            content_length = int(response.headers.get("content-length", 0))
            if content_length > 50 * 1024 * 1024:  # 50MB limit
                raise ValueError(f"Image too large: {content_length / 1024 / 1024:.1f}MB")
            
            if config.debug:
                print(f"[DOWNLOAD] Downloaded {len(response.content) / 1024:.1f}KB")
            
            return response.content
            
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Failed to download image: {e.response.status_code}") from e
        except Exception as e:
            raise ValueError(f"Failed to download image: {e}") from e
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL is a valid image URL"""
        if not url:
            return False
        
        # Skip data URLs
        if url.startswith("data:"):
            return False
        
        # Skip obvious non-images
        skip_patterns = [
            'favicon', 'logo', 'icon', 'banner', 'sprite',
            'button', 'arrow', 'nav', 'menu'
        ]
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in skip_patterns):
            return False
        
        # Check for common image extensions
        valid_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        return any(url.lower().endswith(ext) or f"{ext}?" in url.lower() 
                  for ext in valid_extensions)
    
    def __del__(self):
        """Clean up HTTP client"""
        if hasattr(self, "client"):
            self.client.close()