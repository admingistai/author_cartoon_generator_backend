# Wall Street Journal Style Author Cartoonizer

A streamlined tool that transforms article authors into Wall Street Journal hedcut-style portraits.

## Overview

This tool automatically:
1. **Extracts the author name** from any article URL
2. **Finds the author's photo** using Google Custom Search
3. **Crops the image** to focus on the face  
4. **Generates a WSJ-style cartoon** using Replicate's InstantID model

## Features

- **Authentic WSJ Hedcut Style** - Creates traditional stippled portraits with crosshatching
- **Smart Author Detection** - Extracts author names from JSON-LD, meta tags, and bylines
- **Face Cropping** - Automatically detects and crops faces for better results
- **Google Image Search** - Uses Google Custom Search API for high-quality author photos
- **Simple CLI** - One command operation with minimal setup

## Installation

1. **Clone and navigate to the directory:**
   ```bash
   cd author_cartoon_generator
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file with:
   ```bash
   # Google Custom Search API (required)
   GOOGLE_API_KEY=your_google_api_key_here
   GOOGLE_SEARCH_ENGINE_ID=c61a15b4098d74d98

   # Replicate API (required)
   REPLICATE_API_TOKEN=your_replicate_token_here

   # Optional settings
   DEBUG=false
   REQUEST_TIMEOUT=30
   MAX_SEARCH_RESULTS=5
   ```

## Usage

### Basic Usage

```bash
# Generate WSJ cartoon from article URL
python main.py https://www.wsj.com/articles/example-article

# With custom output path
python main.py https://article-url.com --output portraits/author.png

# Skip face cropping (use full image)
python main.py https://article-url.com --no-crop

# Enable debug output
python main.py https://article-url.com --debug
```

### Example

```bash
python main.py https://www.theatlantic.com/culture/archive/2024/example-article/
```

**Output:** `output/Author_Name_wsj.png`

## How It Works

1. **Author Extraction**: Parses the article HTML to find author name using:
   - JSON-LD structured data (`"author": {"name": "..."}`)
   - Meta tags (`<meta name="author" content="...">`)
   - Byline patterns (`"By Author Name"`)

2. **Image Search**: Uses Google Custom Search with query like:
   - `"Author Name" "Publication Name"`
   - Filters for portrait/face images
   - Selects highest quality result

3. **Face Detection**: Uses OpenCV Haar Cascades to:
   - Detect faces in the image
   - Select the largest face
   - Crop with 30% padding around face

4. **Cartoon Generation**: Sends to Replicate InstantID with:
   - WSJ hedcut style prompt
   - Black and white stippling
   - Clean white background
   - 512x512 output resolution

## API Requirements

### Google Custom Search API
- **Free tier**: 100 searches/day
- **Paid tier**: $5 per 1,000 additional queries
- **Setup**: [Google Cloud Console](https://console.cloud.google.com/)

### Replicate API
- **Pricing**: ~$0.005 per generation
- **Model**: InstantID for face-preserving style transfer
- **Setup**: [Replicate.com](https://replicate.com/)

## Configuration

Set these environment variables in your `.env` file:

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Google Custom Search API key |
| `GOOGLE_SEARCH_ENGINE_ID` | Yes | Search engine ID (use: `c61a15b4098d74d98`) |
| `REPLICATE_API_TOKEN` | Yes | Replicate API token |
| `DEBUG` | No | Enable debug output (default: false) |
| `REQUEST_TIMEOUT` | No | HTTP timeout in seconds (default: 30) |
| `MAX_SEARCH_RESULTS` | No | Max images to search (default: 5) |

## Troubleshooting

### "No faces detected"
- The image might be low quality or not contain a clear face
- Try `--no-crop` to use the full image
- Check the source image with `--debug`

### "No images found for author"
- Author name might not be correctly extracted
- Try articles from major publications (WSJ, Atlantic, NYT, etc.)
- Check extraction with `--debug`

### "API quota exceeded"
- Google: Check your daily quota in Google Cloud Console
- Replicate: Check your account balance and usage

## Supported Publications

The tool works best with major publications that have proper article metadata:
- Wall Street Journal
- The Atlantic
- New York Times
- Washington Post
- CNN, BBC, Reuters
- Forbes, Bloomberg
- Wired, TechCrunch
- And many others...

## Output

Generated cartoons are saved as:
- **Format**: PNG with transparency support
- **Size**: 512x512 pixels
- **Style**: Black and white WSJ hedcut
- **Quality**: High-definition with clean backgrounds

## Examples

**Input**: `https://www.theatlantic.com/culture/archive/2024/example/`
**Output**: `output/Spencer_Kornhaber_wsj.png`

The tool automatically:
1. Extracts "Spencer Kornhaber" as the author
2. Searches for "Spencer Kornhaber" "The Atlantic" 
3. Finds his professional headshot
4. Crops to his face
5. Generates a WSJ-style cartoon portrait

## Version

WSJ Cartoonizer v1.0.0

## License

MIT License