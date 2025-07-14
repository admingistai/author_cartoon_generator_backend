"""Face detection and cropping using OpenCV"""

import cv2
import numpy as np
import io
from typing import Tuple

from PIL import Image

from config import config


class FaceCropper:
    """Face detection and cropping utility using OpenCV"""
    
    def __init__(self):
        """Initialize face detection"""
        # Load OpenCV Haar Cascade for face detection
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if self.face_cascade.empty():
            raise RuntimeError("Failed to load OpenCV face cascade")
    
    def crop_face(self, image_bytes: bytes, padding_percent: float = 0.3) -> bytes:
        """Detect and crop the largest face from image
        
        Args:
            image_bytes: Input image as bytes
            padding_percent: Padding around face (0.3 = 30%)
            
        Returns:
            Cropped face image as bytes
        """
        # Load image from bytes
        image = self._load_image_from_bytes(image_bytes)
        
        # Detect faces
        faces = self._detect_faces(image)
        
        if not faces:
            raise ValueError("No faces detected in image")
        
        # Find the largest face
        largest_face = max(faces, key=lambda face: face[2] * face[3])
        x, y, w, h = largest_face
        
        if config.debug:
            print(f"[FACE CROP] Detected face at ({x}, {y}) with size {w}x{h}")
        
        # Calculate crop coordinates with padding
        padding_x = int(w * padding_percent)
        padding_y = int(h * padding_percent)
        
        crop_x1 = max(0, x - padding_x)
        crop_y1 = max(0, y - padding_y)
        crop_x2 = min(image.shape[1], x + w + padding_x)
        crop_y2 = min(image.shape[0], y + h + padding_y)
        
        # Crop the image
        cropped = image[crop_y1:crop_y2, crop_x1:crop_x2]
        
        if config.debug:
            print(f"[FACE CROP] Cropped to {cropped.shape[1]}x{cropped.shape[0]}")
        
        # Convert back to bytes
        return self._image_to_bytes(cropped)
    
    def _load_image_from_bytes(self, image_bytes: bytes) -> np.ndarray:
        """Load image from bytes using OpenCV"""
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        
        # Decode image
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Failed to decode image")
        
        return image
    
    def _detect_faces(self, image: np.ndarray) -> list:
        """Detect faces in image using OpenCV Haar Cascade"""
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        return faces.tolist() if len(faces) > 0 else []
    
    def _image_to_bytes(self, image: np.ndarray) -> bytes:
        """Convert OpenCV image to bytes"""
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        pil_image = Image.fromarray(rgb_image)
        
        # Save to bytes
        buffer = io.BytesIO()
        pil_image.save(buffer, format='PNG')
        
        return buffer.getvalue()