"""Wall Street Journal style cartoon generation using Replicate API"""

import io
from pathlib import Path

import replicate
import httpx
from PIL import Image

from config import config


class WSJCartoonizer:
    """Generate Wall Street Journal hedcut style cartoons using Replicate"""
    
    # WSJ hedcut style prompt optimized for FLUX Kontext Pro image transformation
    WSJ_PROMPT = """Transform this portrait photograph into a classic Wall Street Journal hedcut style illustration:
    Convert to black and white stipple portrait with crosshatch shading and pointillism technique,
    newspaper engraving style with detailed pen and ink stippling,
    pure black ink on clean white background, professional newspaper portrait,
    head and shoulders composition, high contrast stippling pattern,
    remove all color and create traditional WSJ editorial illustration style"""
    
    WSJ_NEGATIVE = """color, colored, photography, realistic, 3d render, painting,
    watercolor, gradient, gray, grayscale, cartoon, anime, sketch, rough, messy,
    soft edges, blur, anti-aliasing, BACKGROUND OBJECTS, scenery, landscape,
    furniture, buildings, decorations, patterns, textures in background,
    busy background, complex scene, environment, room, outdoor scene,
    props, accessories in background"""
    
    def __init__(self, api_token: str):
        """Initialize with Replicate API token"""
        if not api_token:
            raise ValueError("Replicate API token is required")
        
        self.client = replicate.Client(api_token=api_token)
    
    def generate_cartoon(self, face_image: bytes) -> bytes:
        """Generate WSJ-style cartoon from face image
        
        Args:
            face_image: Face image as bytes
            
        Returns:
            Cartoon image as bytes
        """
        try:
            if config.debug:
                print("[WSJ CARTOON] Starting cartoon generation...")
            
            # Convert bytes to PIL Image for upload
            image = Image.open(io.BytesIO(face_image))
            
            # Ensure RGB mode
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Save to bytes buffer for upload
            img_buffer = io.BytesIO()
            image.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            
            if config.debug:
                print("[WSJ CARTOON] Sending to FLUX Kontext Pro model...")
            
            # Generate using FLUX Kontext Pro model
            output = self.client.run(
                "black-forest-labs/flux-kontext-pro",
                input={
                    "input_image": img_buffer,
                    "prompt": self.WSJ_PROMPT,
                    "aspect_ratio": "match_input_image",
                    "safety_tolerance": 2,
                    "prompt_upsampling": True,
                    "output_format": "png"
                }
            )
            
            if not output:
                raise ValueError("No output from Replicate")
            
            # Get the output URL - FLUX Kontext Pro returns FileOutput directly
            if hasattr(output, 'url'):
                # It's a FileOutput object - get the actual URL
                image_url = output.url
            elif isinstance(output, list) and len(output) > 0:
                # Handle list format from other models
                image_url = output[0]
                if hasattr(image_url, 'url'):
                    image_url = image_url.url
            else:
                # Direct URL string
                image_url = str(output)
            
            if config.debug:
                print(f"[WSJ CARTOON] Generated image URL: {image_url}")
            
            # Download the generated image
            return self._download_image(image_url)
            
        except Exception as e:
            raise ValueError(f"Failed to generate cartoon: {e}") from e
    
    def _download_image(self, url: str) -> bytes:
        """Download image from URL"""
        try:
            if config.debug:
                print(f"[WSJ CARTOON] Downloading generated image...")
            
            response = httpx.get(url, timeout=30)
            response.raise_for_status()
            
            if config.debug:
                print(f"[WSJ CARTOON] Downloaded {len(response.content) / 1024:.1f}KB")
            
            return response.content
            
        except Exception as e:
            raise ValueError(f"Failed to download generated image: {e}") from e
    
    def save_cartoon(self, image_bytes: bytes, output_path: str) -> str:
        """Save cartoon image to file
        
        Args:
            image_bytes: Cartoon image as bytes
            output_path: Output file path
            
        Returns:
            Actual output path used
        """
        try:
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Open image from bytes
            image = Image.open(io.BytesIO(image_bytes))
            
            # Ensure it's in RGB mode
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Save as PNG for best quality
            if not output_path.lower().endswith(".png"):
                output_path = output_path + ".png"
            
            image.save(output_path, "PNG", optimize=True)
            
            if config.debug:
                print(f"[WSJ CARTOON] Saved to: {output_path}")
            
            return output_path
            
        except Exception as e:
            raise ValueError(f"Failed to save cartoon: {e}") from e