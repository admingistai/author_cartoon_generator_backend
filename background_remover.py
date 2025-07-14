"""Background removal module for creating transparent cartoon images"""

import io
from typing import Union, Tuple
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion, binary_dilation

from config import config


class BackgroundRemover:
    """Removes white/light backgrounds from cartoon images to create transparent PNGs"""
    
    def __init__(self, tolerance: int = 30, edge_smoothing: bool = True):
        """
        Initialize background remover
        
        Args:
            tolerance: Color tolerance for white detection (0-255)
            edge_smoothing: Whether to apply edge smoothing to reduce aliasing
        """
        self.tolerance = tolerance
        self.edge_smoothing = edge_smoothing
    
    def remove_white_background(self, image_input: Union[bytes, Image.Image, str, Path]) -> Image.Image:
        """
        Remove white/near-white background and return image with transparency
        
        Args:
            image_input: Input image as bytes, PIL Image, or file path
            
        Returns:
            PIL Image with RGBA channels and transparent background
        """
        # Load image
        if isinstance(image_input, bytes):
            image = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, (str, Path)):
            image = Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            image = image_input.copy()
        else:
            raise ValueError("Invalid input type. Expected bytes, PIL Image, or file path")
        
        # Convert to RGBA if needed
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        if config.debug:
            print(f"[BACKGROUND REMOVAL] Processing image: {image.mode} {image.size}")
        
        # Convert to numpy array
        data = np.array(image)
        
        # Create mask for white/near-white pixels
        # Check if R, G, B channels are all close to white (255)
        white_threshold = 255 - self.tolerance
        mask = (
            (data[:, :, 0] > white_threshold) & 
            (data[:, :, 1] > white_threshold) & 
            (data[:, :, 2] > white_threshold)
        )
        
        # Apply edge smoothing if enabled
        if self.edge_smoothing:
            # Erode mask slightly to avoid removing edge pixels
            mask = binary_erosion(mask, iterations=1)
            # Dilate back to smooth edges
            mask = binary_dilation(mask, iterations=1)
        
        # Count pixels to be removed for debugging
        if config.debug:
            pixels_removed = np.sum(mask)
            total_pixels = mask.shape[0] * mask.shape[1]
            percent_removed = (pixels_removed / total_pixels) * 100
            print(f"[BACKGROUND REMOVAL] Removed {pixels_removed} pixels ({percent_removed:.1f}% of image)")
        
        # Set alpha channel to 0 (transparent) for white pixels
        data[mask, 3] = 0
        
        # Create new image from modified data
        result = Image.fromarray(data, 'RGBA')
        
        return result
    
    def process_cartoon(self, cartoon_bytes: bytes) -> bytes:
        """
        Process cartoon image bytes and return transparent PNG bytes
        
        Args:
            cartoon_bytes: Input cartoon image as bytes
            
        Returns:
            Transparent PNG image as bytes
        """
        # Remove background
        transparent_image = self.remove_white_background(cartoon_bytes)
        
        # Convert back to bytes
        output_buffer = io.BytesIO()
        transparent_image.save(output_buffer, format='PNG', optimize=True)
        return output_buffer.getvalue()
    
    def save_transparent(self, image_input: Union[bytes, Image.Image], output_path: str) -> str:
        """
        Remove background and save as transparent PNG
        
        Args:
            image_input: Input image
            output_path: Output file path
            
        Returns:
            Path to saved file
        """
        # Process image
        transparent_image = self.remove_white_background(image_input)
        
        # Ensure output path has .png extension
        output_path = Path(output_path)
        if output_path.suffix.lower() != '.png':
            output_path = output_path.with_suffix('.png')
        
        # Save with PNG format to preserve transparency
        transparent_image.save(output_path, 'PNG', optimize=True)
        
        if config.debug:
            print(f"[BACKGROUND REMOVAL] Saved transparent image to: {output_path}")
        
        return str(output_path)