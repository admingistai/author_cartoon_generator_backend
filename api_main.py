#!/usr/bin/env python3
"""FastAPI Application for WSJ Author Cartoonizer"""

import io
import traceback
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, Field

from config import config
from author_extractor import AuthorExtractor
from image_finder import ImageFinder
from face_cropper import FaceCropper
from wsj_cartoonizer import WSJCartoonizer


# Pydantic models
class CartoonRequest(BaseModel):
    url: HttpUrl = Field(..., description="Article URL to extract author from")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.theatlantic.com/culture/archive/2024/01/example-article/"
            }
        }


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: str = Field(..., description="Detailed error description")
    status_code: int = Field(..., description="HTTP status code")


# Global components - initialized at startup
components = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize components at startup"""
    try:
        # Validate configuration
        config.validate()
        
        # Initialize components
        components["author_extractor"] = AuthorExtractor()
        components["image_finder"] = ImageFinder()
        components["face_cropper"] = FaceCropper()
        components["cartoonizer"] = WSJCartoonizer(config.replicate_api_token)
        
        print("✅ FastAPI startup: All components initialized successfully")
        yield
        
    except Exception as e:
        print(f"❌ FastAPI startup failed: {e}")
        raise
    finally:
        # Cleanup if needed
        components.clear()


# FastAPI app
app = FastAPI(
    title="WSJ Author Cartoonizer API",
    description="Transform article authors into Wall Street Journal hedcut-style cartoon portraits",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "WSJ Author Cartoonizer API",
        "version": "1.0.0",
        "description": "Transform article authors into cartoon portraits",
        "endpoints": {
            "generate": "POST /generate-cartoon",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Basic configuration check
        if not config.replicate_api_token:
            raise ValueError("Replicate API token not configured")
        if not config.google_api_key:
            raise ValueError("Google API key not configured")
            
        return {
            "status": "healthy",
            "message": "All systems operational",
            "components": {
                "replicate": bool(config.replicate_api_token),
                "google_search": bool(config.google_api_key),
                "cartoon_generation": True
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {e}")


@app.post("/debug-search")
async def debug_search(request: CartoonRequest):
    """Debug endpoint to test Google image search without generating cartoon"""
    try:
        url = str(request.url)
        
        # Extract author name
        author_name, publisher = components["author_extractor"].extract_author(url)
        if not author_name:
            return {"error": "Could not extract author name"}
        
        # Test image search using actual ImageFinder class
        try:
            # Use the actual ImageFinder to see where it fails
            try:
                image_url = components["image_finder"].find_author_image(author_name, publisher)
                image_found = True
                image_url_result = image_url
                image_error = None
            except Exception as e:
                image_found = False
                image_url_result = None
                image_error = str(e)
            
            # Also make direct API call for comparison
            import httpx
            if publisher:
                query = f'"{author_name}" "{publisher}"'
            else:
                query = f'"{author_name}"'
                
            params = {
                "key": config.google_api_key,
                "cx": config.google_search_engine_id,
                "q": query,
                "searchType": "image",
                "num": config.max_search_results,
                "imgSize": "large",
                "imgType": "face"
            }
            
            client = httpx.Client(timeout=30)
            response = client.get("https://www.googleapis.com/customsearch/v1", params=params)
            response.raise_for_status()
            data = response.json()
            client.close()
            
            # Return comparison
            debug_info = {
                "author_name": author_name,
                "publisher": publisher,
                "query": query,
                "image_finder_result": {
                    "success": image_found,
                    "image_url": image_url_result,
                    "error": image_error
                },
                "direct_api_result": {
                    "items_count": len(data.get("items", [])),
                    "search_info": data.get("searchInformation", {}),
                    "error": data.get("error"),
                    "first_few_urls": [item.get("link") for item in data.get("items", [])[:3]]
                },
                "config": {
                    "max_search_results": config.max_search_results,
                    "debug": config.debug
                }
            }
            
            return debug_info
            
        except Exception as e:
            return {
                "error": f"Search failed: {str(e)}",
                "author_name": author_name,
                "publisher": publisher
            }
            
    except Exception as e:
        return {"error": f"Failed to extract author: {str(e)}"}


@app.post("/generate-cartoon", 
          response_class=Response,
          responses={
              200: {
                  "content": {"image/png": {}},
                  "description": "PNG cartoon image"
              },
              400: {"model": ErrorResponse, "description": "Invalid request"},
              404: {"model": ErrorResponse, "description": "Author not found"},
              422: {"model": ErrorResponse, "description": "Validation error"},
              500: {"model": ErrorResponse, "description": "Internal server error"}
          })
async def generate_cartoon(request: CartoonRequest):
    """
    Generate a WSJ-style cartoon from an article author's photo
    
    Takes an article URL, extracts the author, finds their photo,
    and returns a PNG cartoon in WSJ hedcut style.
    """
    try:
        url = str(request.url)
        
        # Step 1: Extract author name
        try:
            author_name, publisher = components["author_extractor"].extract_author(url)
            if not author_name:
                raise HTTPException(
                    status_code=404,
                    detail="Could not extract author name from the provided URL"
                )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to extract author from URL: {str(e)}"
            )
        
        # Step 2: Find author image
        try:
            print(f"[GENERATE-CARTOON] Starting image search for: {author_name}")
            print(f"[GENERATE-CARTOON] Components available: {list(components.keys())}")
            print(f"[GENERATE-CARTOON] ImageFinder type: {type(components.get('image_finder'))}")
            
            image_url = components["image_finder"].find_author_image(author_name, publisher)
            print(f"[GENERATE-CARTOON] ImageFinder returned: {image_url}")
            
            if not image_url:
                print(f"[GENERATE-CARTOON] Empty image_url returned")
                raise HTTPException(
                    status_code=404,
                    detail=f"Could not find image for author: {author_name}"
                )
        except Exception as e:
            print(f"[GENERATE-CARTOON] ImageFinder exception: {str(e)}")
            print(f"[GENERATE-CARTOON] Exception type: {type(e)}")
            raise HTTPException(
                status_code=404,
                detail=f"Failed to find author image: {str(e)}"
            )
        
        # Step 3: Download image
        try:
            image_bytes = components["image_finder"].download_image(image_url)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to download author image: {str(e)}"
            )
        
        # Step 4: Crop face (optional, use full image if cropping fails)
        try:
            cropped_image = components["face_cropper"].crop_face(image_bytes)
            image_bytes = cropped_image
        except Exception as e:
            # Continue with original image if face cropping fails
            if config.debug:
                print(f"Face cropping failed, using full image: {e}")
        
        # Step 5: Generate WSJ cartoon
        try:
            cartoon_bytes = components["cartoonizer"].generate_cartoon(image_bytes)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate cartoon: {str(e)}"
            )
        
        # Step 6: Return PNG image
        return Response(
            content=cartoon_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename={author_name.replace(' ', '_')}_wsj_cartoon.png",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Catch any unexpected errors
        error_detail = str(e)
        if config.debug:
            error_detail += f"\n\nTraceback:\n{traceback.format_exc()}"
        
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error occurred: {error_detail}"
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail.split(":")[0] if ":" in exc.detail else "Request failed",
            detail=exc.detail,
            status_code=exc.status_code
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """General exception handler for unexpected errors"""
    error_detail = str(exc)
    if config.debug:
        error_detail += f"\n\nTraceback:\n{traceback.format_exc()}"
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=error_detail,
            status_code=500
        ).dict()
    )


if __name__ == "__main__":
    # For local development
    uvicorn.run(
        "api_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )