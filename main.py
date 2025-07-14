#!/usr/bin/env python3
"""Wall Street Journal Style Author Cartoonizer CLI"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import config
from author_extractor import AuthorExtractor
from image_finder import ImageFinder
from face_cropper import FaceCropper
from wsj_cartoonizer import WSJCartoonizer
from background_remover import BackgroundRemover

# Initialize CLI app
app = typer.Typer(
    name="wsj-cartoonizer",
    help="Generate Wall Street Journal style cartoon portraits from article authors",
    add_completion=False
)

# Initialize console for pretty output
console = Console()


def print_error(message: str):
    """Print error message in red"""
    console.print(f"[red]Error:[/red] {message}")


def print_success(message: str):
    """Print success message in green"""
    console.print(f"[green]✓[/green] {message}")


def print_info(message: str):
    """Print info message"""
    console.print(f"[blue]ℹ[/blue] {message}")


@app.command()
def cartoonize(
    url: str = typer.Argument(..., help="Article URL to extract author from"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output file path (default: output/<author_name>_wsj.png)"
    ),
    debug: bool = typer.Option(
        False, "--debug", "-d",
        help="Enable debug output"
    ),
    no_crop: bool = typer.Option(
        False, "--no-crop",
        help="Skip face cropping (use full image)"
    ),
    transparent: bool = typer.Option(
        False, "--transparent", "--remove-bg",
        help="Remove white background to create transparent PNG"
    )
):
    """Generate WSJ-style cartoon from article author's photo"""
    
    # Update debug setting
    config.debug = debug
    
    try:
        # Validate configuration
        config.validate()
        
        # Initialize components
        author_extractor = AuthorExtractor()
        image_finder = ImageFinder()
        face_cropper = FaceCropper()
        cartoonizer = WSJCartoonizer(config.replicate_api_token)
        if transparent:
            bg_remover = BackgroundRemover(
                tolerance=config.background_removal_tolerance,
                edge_smoothing=config.background_removal_edge_smoothing
            )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Step 1: Extract author name
            task = progress.add_task("Extracting author from article...", total=None)
            author_name, publisher = author_extractor.extract_author(url)
            progress.update(task, completed=1)
            print_success(f"Found author: {author_name}")
            if publisher:
                print_info(f"Publisher: {publisher}")
            
            # Step 2: Find author image
            task = progress.add_task("Searching for author image...", total=None)
            image_url = image_finder.find_author_image(author_name, publisher)
            progress.update(task, completed=1)
            print_success("Found author image")
            
            # Step 3: Download and process image
            task = progress.add_task("Downloading image...", total=None)
            image_bytes = image_finder.download_image(image_url)
            progress.update(task, completed=1)
            
            # Step 4: Crop to face (optional)
            if not no_crop:
                task = progress.add_task("Detecting and cropping face...", total=None)
                try:
                    cropped_image = face_cropper.crop_face(image_bytes)
                    image_bytes = cropped_image
                    progress.update(task, completed=1)
                    print_success("Face detected and cropped")
                except Exception as e:
                    progress.update(task, completed=1)
                    print_info(f"Could not crop face: {e}. Using full image.")
            
            # Step 5: Generate WSJ cartoon
            task = progress.add_task("Generating WSJ-style cartoon...", total=None)
            cartoon_bytes = cartoonizer.generate_cartoon(image_bytes)
            progress.update(task, completed=1)
            print_success("Cartoon generated successfully")
            
            # Step 6: Background removal (if requested)
            if transparent:
                task = progress.add_task("Removing white background...", total=None)
                cartoon_bytes = bg_remover.process_cartoon(cartoon_bytes)
                progress.update(task, completed=1)
                print_success("Background removed successfully")
            
            # Step 7: Save output
            if not output:
                # Generate default output path
                safe_name = author_name.replace(" ", "_").replace("/", "_")
                suffix = "_transparent" if transparent else ""
                output = config.output_dir / f"{safe_name}_wsj{suffix}.png"
            
            output_path = cartoonizer.save_cartoon(cartoon_bytes, str(output))
            print_success(f"Saved cartoon to: {output_path}")
            
    except Exception as e:
        print_error(str(e))
        if debug:
            console.print_exception()
        sys.exit(1)


@app.command()
def version():
    """Show version information"""
    console.print("WSJ Cartoonizer v1.0.0")


if __name__ == "__main__":
    app()