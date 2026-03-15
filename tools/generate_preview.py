#!/usr/bin/env python3
"""
Preview Image Generator for CSOH Resources

Automatically captures and optimizes screenshots of resource URLs
to use as preview images.

Features:
- Multiple capture methods (Playwright, Screenshot API)
- Image optimization and resizing
- Automatic preview-mapping.json updates
- Fallback to placeholder images

Usage:
    python3 tools/generate_preview.py <url> [output_filename]
    python3 tools/generate_preview.py --check resources.html
    python3 tools/generate_preview.py --batch urls.txt
"""

import sys
import os
import json
from pathlib import Path
from urllib.parse import urlparse
import time

# Configuration
PREVIEW_DIR = Path(__file__).parent.parent / 'img' / 'previews'
PREVIEW_MAPPING = Path(__file__).parent.parent / 'preview-mapping.json'
TARGET_WIDTH = 400
TARGET_HEIGHT = 300
SCREENSHOT_TIMEOUT = 30  # seconds
MIN_PREVIEW_SIZE_KB = 12


def is_preview_good(preview_path):
    """Check if a preview file exists and meets basic quality thresholds."""
    full_path = Path(__file__).parent.parent / preview_path
    if not full_path.exists():
        return False

    try:
        file_size = os.path.getsize(full_path)
        if file_size < MIN_PREVIEW_SIZE_KB * 1024:
            return False
    except OSError:
        return False

    return True

def generate_filename_from_url(url):
    """Generate a safe filename from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '')
    path = parsed.path.strip('/').replace('/', '-')
    
    if path:
        filename = f"{domain}-{path}"
    else:
        filename = domain
    
    # Clean up filename
    filename = filename.lower()
    filename = ''.join(c if c.isalnum() or c in ['-', '_'] else '-' for c in filename)
    filename = filename[:100]  # Limit length
    
    return f"{filename}.jpg"

def capture_with_playwright(url, output_path):
    """Capture screenshot using Playwright (best quality)."""
    try:
        from playwright.sync_api import sync_playwright
        
        print(f"  📸 Using Playwright to capture {url}")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = context.new_page()
            
            # Set timeout
            page.set_default_timeout(SCREENSHOT_TIMEOUT * 1000)
            
            # Navigate and wait for content
            page.goto(url, wait_until='networkidle')
            
            # Wait a bit for any JS to render
            time.sleep(2)
            
            # Take screenshot
            page.screenshot(path=str(output_path), full_page=False)
            
            browser.close()
        
        return True, "Screenshot captured with Playwright"
    
    except ImportError:
        return False, "Playwright not installed (pip install playwright)"
    except Exception as e:
        return False, f"Playwright error: {str(e)}"

def capture_with_screenshot_api(url, output_path):
    """Capture screenshot using screenshot.guru free API (no auth needed)."""
    try:
        import urllib.request
        
        print(f"  🌐 Using Screenshot API for {url}")
        
        # screenshot.guru free API endpoint
        api_url = f"https://image.thum.io/get/width/800/crop/600/{url}"
        
        # Download screenshot
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        request = urllib.request.Request(api_url, headers=headers)
        
        with urllib.request.urlopen(request, timeout=SCREENSHOT_TIMEOUT) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())
        
        return True, "Screenshot captured with API"
    
    except Exception as e:
        return False, f"API error: {str(e)}"

def capture_with_screencapture(url, output_path):
    """Fallback: Use macOS screencapture with Safari (macOS only)."""
    try:
        print(f"  🖥️  Using macOS Safari to capture {url}")
        
        # Open URL in Safari and take screenshot (requires macOS)
        # This is a fallback and requires manual interaction
        # Not recommended for automation
        
        return False, "macOS screencapture requires manual interaction"
    
    except Exception as e:
        return False, f"screencapture error: {str(e)}"

def create_placeholder_image(output_path, message="Preview Not Available"):
    """Create a simple placeholder image."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Create blank image
        img = Image.new('RGB', (TARGET_WIDTH, TARGET_HEIGHT), color='#2c3e50')
        draw = ImageDraw.Draw(img)
        
        # Add text
        try:
            # Try to use a nice font
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except:
            font = ImageFont.load_default()
        
        # Center text
        text = message
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        position = ((TARGET_WIDTH - text_width) // 2, (TARGET_HEIGHT - text_height) // 2)
        draw.text(position, text, fill='#ecf0f1', font=font)
        
        # Save
        img.save(output_path, 'JPEG', quality=85, optimize=True)
        
        return True, "Created placeholder image"
    
    except ImportError:
        return False, "Pillow not installed (pip install Pillow)"
    except Exception as e:
        return False, f"Placeholder error: {str(e)}"

def optimize_image(image_path):
    """Optimize and resize image to target dimensions."""
    try:
        from PIL import Image
        
        print(f"  🔧 Optimizing image...")
        
        # Open image
        img = Image.open(image_path)
        
        # Convert to RGB if needed
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Calculate resize dimensions (maintain aspect ratio)
        aspect = img.width / img.height
        if aspect > TARGET_WIDTH / TARGET_HEIGHT:
            # Width is limiting factor
            new_width = TARGET_WIDTH
            new_height = int(TARGET_WIDTH / aspect)
        else:
            # Height is limiting factor
            new_height = TARGET_HEIGHT
            new_width = int(TARGET_HEIGHT * aspect)
        
        # Resize with high-quality algorithm
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Save optimized
        img.save(image_path, 'JPEG', quality=85, optimize=True)
        
        file_size = os.path.getsize(image_path)
        print(f"  ✅ Optimized to {file_size // 1024}KB ({new_width}x{new_height})")
        
        return True, f"Optimized to {file_size // 1024}KB"
    
    except ImportError:
        return False, "Pillow not installed"
    except Exception as e:
        return False, f"Optimization error: {str(e)}"

def update_preview_mapping(url, image_filename):
    """Update preview-mapping.json with new entry."""
    try:
        # Load existing mapping
        if PREVIEW_MAPPING.exists():
            with open(PREVIEW_MAPPING, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
        else:
            mapping = {}
        
        # Add new entry
        mapping[url] = f"img/previews/{image_filename}"
        
        # Sort by URL for consistency
        mapping = dict(sorted(mapping.items()))
        
        # Save
        with open(PREVIEW_MAPPING, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, indent=2, ensure_ascii=False)
            f.write('\n')  # Add trailing newline
        
        print(f"  📋 Updated preview-mapping.json")
        return True
    
    except Exception as e:
        print(f"  ⚠️  Could not update preview-mapping.json: {e}")
        return False

def check_existing_preview(url):
    """Check if a good preview already exists for this URL."""
    if not PREVIEW_MAPPING.exists():
        return None
    
    try:
        with open(PREVIEW_MAPPING, 'r', encoding='utf-8') as f:
            mapping = json.load(f)
        
        preview_path = mapping.get(url)
        if preview_path and is_preview_good(preview_path):
            return preview_path
        
        return None
    
    except Exception:
        return None

def generate_preview(url, output_filename=None, force=False):
    """
    Generate preview image for a URL.
    
    Args:
        url: URL to capture
        output_filename: Optional custom filename
        force: Force regeneration even if exists
    
    Returns:
        (success, image_path, message)
    """
    print(f"\n🖼️  Generating preview for: {url}")
    
    # Check if preview already exists
    if not force:
        existing = check_existing_preview(url)
        if existing:
            print(f"  ✅ Preview already exists: {existing}")
            return True, existing, "Preview already exists"
    
    # Generate filename
    if not output_filename:
        output_filename = generate_filename_from_url(url)
    
    # Ensure it ends with .jpg
    if not output_filename.endswith('.jpg'):
        output_filename += '.jpg'
    
    # Create output path
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PREVIEW_DIR / output_filename
    
    print(f"  📁 Output: img/previews/{output_filename}")
    
    # Try capture methods in order of preference
    methods = [
        capture_with_playwright,
        capture_with_screenshot_api,
        # capture_with_screencapture,  # Skip manual method
    ]
    
    success = False
    for method in methods:
        result, message = method(url, output_path)
        if result:
            print(f"  ✅ {message}")
            success = True
            break
        else:
            print(f"  ⚠️  {message}")
    
    # If all methods failed, create placeholder
    if not success:
        print(f"  📝 Creating placeholder image...")
        result, message = create_placeholder_image(output_path)
        if not result:
            return False, None, "Failed to create preview or placeholder"
        print(f"  ✅ {message}")
    
    # Optimize image
    optimize_result, optimize_msg = optimize_image(output_path)
    if not optimize_result:
        print(f"  ⚠️  {optimize_msg}")
    
    # Update mapping
    update_preview_mapping(url, output_filename)
    
    relative_path = f"img/previews/{output_filename}"
    return True, relative_path, "Preview generated successfully"

def extract_urls_from_resources_html():
    """Extract all URLs from resources.html without good previews."""
    resources_file = Path(__file__).parent.parent / 'resources.html'
    
    if not resources_file.exists():
        return []
    
    import re
    
    with open(resources_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all resource card URLs (class and target can appear in either order)
    pattern = r'<a\s+href="([^"]+)"[^>]*class="card-link"'
    urls = re.findall(pattern, content)
    
    # Filter to only those without previews
    urls_needing_previews = []
    for url in urls:
        if not check_existing_preview(url):
            urls_needing_previews.append(url)
    
    return urls_needing_previews

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 tools/generate_preview.py <url> [output_filename]")
        print("  python3 tools/generate_preview.py --check resources.html")
        print("  python3 tools/generate_preview.py --batch urls.txt")
        return 1
    
    if sys.argv[1] == '--check':
        print("🔍 Checking for resources without previews...")
        urls = extract_urls_from_resources_html()
        
        if not urls:
            print("✅ All resources have preview images!")
            return 0
        
        print(f"\n📋 Found {len(urls)} resources without previews:\n")
        for url in urls:
            print(f"  • {url}")
        
        print(f"\n💡 Generate previews with:")
        print(f"   python3 tools/generate_preview.py --batch-auto")
        
        return 0
    
    elif sys.argv[1] == '--batch-auto':
        print("🔄 Generating previews for all resources without images...")
        urls = extract_urls_from_resources_html()
        
        if not urls:
            print("✅ All resources have preview images!")
            return 0
        
        print(f"\n📋 Processing {len(urls)} URLs...\n")
        
        success_count = 0
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing {url}")
            result, path, message = generate_preview(url)
            if result:
                success_count += 1
            time.sleep(1)  # Rate limiting
        
        print(f"\n✅ Generated {success_count}/{len(urls)} previews")
        return 0
    
    else:
        # Single URL
        url = sys.argv[1]
        output_filename = sys.argv[2] if len(sys.argv) > 2 else None
        
        result, path, message = generate_preview(url, output_filename, force=True)
        
        if result:
            print(f"\n✅ Success! Preview saved to: {path}")
            return 0
        else:
            print(f"\n❌ Failed: {message}")
            return 1

if __name__ == '__main__':
    sys.exit(main())
