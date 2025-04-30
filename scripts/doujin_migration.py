#!/usr/bin/env python

import os
import sys
import json
import re
import django
import tempfile
import concurrent.futures
import time
from PIL import Image
from slugify import slugify
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cuteblog.settings')
django.setup()

# Import Django models
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from blog.models import Manga, MangaTag, MangaAuthor, add_points_for_post

# Configuration
TSUMINO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tsumino')
ADMIN_USERNAME = 'shigure'  # Admin username
MAX_WORKERS = 6  # Number of parallel workers (adjust based on your CPU cores)

def create_pdf_from_images(image_files):
    """Create a PDF file from a list of image files"""
    if not image_files:
        return None
    
    # Sort image files numerically
    image_files.sort(key=lambda x: int(re.search(r'\d+', os.path.basename(x)).group()))
    
    # Create a temporary file for the PDF
    pdf_buffer = io.BytesIO()
    
    # Get dimensions from first image
    first_img = Image.open(image_files[0])
    width, height = first_img.size
    
    # Create PDF with the same size as images
    c = canvas.Canvas(pdf_buffer, pagesize=(width, height))
    
    # Add each image as a page
    for img_path in image_files:
        img = Image.open(img_path)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as temp_img:
            # Convert to RGB if image is RGBA to avoid JPEG errors
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            img.save(temp_img.name, 'JPEG')
            c.drawImage(temp_img.name, 0, 0, width, height)
            c.showPage()
    
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer

def process_manga_folder(folder_path, admin_user):
    """Process a single manga folder and create a manga entry"""
    folder_name = os.path.basename(folder_path)
    print(f"Processing manga folder: {folder_name}")
    
    # Check if contentV2.json exists
    content_file = os.path.join(folder_path, 'contentV2.json')
    if not os.path.exists(content_file):
        print(f"  Error: contentV2.json not found in {folder_name}")
        return False
    
    # Load content JSON
    try:
        with open(content_file, 'r', encoding='utf-8') as f:
            content_data = json.load(f)
    except Exception as e:
        print(f"  Error reading contentV2.json in {folder_name}: {e}")
        return False
    
    # Extract metadata
    title = content_data.get('title', folder_name)
    
    # Process tags - extract from attributes structure
    tags = []
    attributes = content_data.get('attributes', {})
    
    # Process tags from TAG attribute
    tag_list = attributes.get('TAG', [])
    if isinstance(tag_list, list):
        for tag_item in tag_list:
            if isinstance(tag_item, dict) and 'name' in tag_item:
                tag_name = tag_item['name'].strip()
                # Split multi-word tags and add them individually
                for t in tag_name.split():
                    if t.strip():
                        tags.append(t.strip())
    
    # Process authors from ARTIST attribute
    artists = []
    artist_list = attributes.get('ARTIST', [])
    if isinstance(artist_list, list):
        for artist_item in artist_list:
            if isinstance(artist_item, dict) and 'name' in artist_item:
                # Replace spaces with underscores in author names
                artist_name = artist_item['name'].strip().replace(' ', '_')
                if artist_name:
                    artists.append(artist_name)
    
    # Create slug from title
    slug = slugify(title)
    
    # Check if manga with this slug already exists
    if Manga.objects.filter(slug=slug).exists():
        print(f"  Manga with slug '{slug}' already exists. Skipping {folder_name}.")
        return False
    
    # Find all image files in the folder (excluding thumb.jpg)
    image_files = []
    for file in os.listdir(folder_path):
        if file.lower() != 'thumb.jpg' and file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')) and re.match(r'\d+', file):
            image_files.append(os.path.join(folder_path, file))
    
    if not image_files:
        print(f"  No image files found in {folder_name}")
        return False
    
    # Create PDF from images
    pdf_buffer = create_pdf_from_images(image_files)
    if not pdf_buffer:
        print(f"  Failed to create PDF from images in {folder_name}")
        return False
    
    # Check for thumb.jpg for thumbnail
    thumbnail_buffer = io.BytesIO()
    thumbnail_path = os.path.join(folder_path, 'thumb.jpg')
    
    try:
        if os.path.exists(thumbnail_path):
            # Use existing thumb.jpg
            thumb_img = Image.open(thumbnail_path)
            # Convert to RGB if image is RGBA to avoid JPEG errors
            if thumb_img.mode == 'RGBA':
                thumb_img = thumb_img.convert('RGB')
            thumb_img.save(thumbnail_buffer, format='JPEG')
            thumbnail_buffer.seek(0)
        else:
            # Create thumbnail from first image
            first_img = Image.open(image_files[0])
            # Convert to RGB if image is RGBA to avoid JPEG errors
            if first_img.mode == 'RGBA':
                first_img = first_img.convert('RGB')
            # Resize for thumbnail
            first_img.thumbnail((800, 800), Image.LANCZOS)
            first_img.save(thumbnail_buffer, format='JPEG')
            thumbnail_buffer.seek(0)
    except Exception as e:
        print(f"  Error creating thumbnail for {folder_name}: {e}")
        thumbnail_buffer = None
    
    # Create manga entry
    try:
        manga = Manga.objects.create(
            title=title,
            slug=slug,
            description=f"Imported from Tsumino folder: {folder_name}",
            user=admin_user
        )
        
        # Add PDF file
        manga.pdf_file.save(f"{slug}.pdf", ContentFile(pdf_buffer.getvalue()))
        
        # Add thumbnail if available
        if thumbnail_buffer:
            manga.thumbnail.save(f"{slug}_thumbnail.jpg", ContentFile(thumbnail_buffer.getvalue()))
        
        # Add tags
        for tag_name in tags:
            tag, created = MangaTag.objects.get_or_create(name=tag_name)
            manga.manga_tags.add(tag)
        
        # Add authors
        for author_name in artists:
            author, created = MangaAuthor.objects.get_or_create(name=author_name)
            manga.manga_authors.add(author)
        
        # Award points for creating a manga
        add_points_for_post(admin_user)
        
        print(f"  Successfully created manga: {title} from {folder_name}")
        return True
    except Exception as e:
        print(f"  Error creating manga entry for {folder_name}: {e}")
        return False

def main():
    start_time = time.time()
    print("Starting Tsumino doujin migration...")
    
    # Check if Tsumino directory exists
    if not os.path.exists(TSUMINO_DIR):
        print(f"Error: Tsumino directory not found at {TSUMINO_DIR}")
        return
    
    # Get admin user
    try:
        admin_user = User.objects.get(username=ADMIN_USERNAME)
    except User.DoesNotExist:
        print(f"Error: Admin user '{ADMIN_USERNAME}' not found. Please update the ADMIN_USERNAME in the script.")
        return
    
    # Get all manga folders
    manga_folders = []
    for folder_name in os.listdir(TSUMINO_DIR):
        folder_path = os.path.join(TSUMINO_DIR, folder_name)
        if os.path.isdir(folder_path):
            manga_folders.append(folder_path)
    
    total_folders = len(manga_folders)
    print(f"Found {total_folders} manga folders to process")
    
    # Process manga folders in parallel
    success_count = 0
    error_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all folder processing tasks
        future_to_folder = {executor.submit(process_manga_folder, folder, admin_user): folder for folder in manga_folders}
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_folder):
            folder = future_to_folder[future]
            try:
                if future.result():
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                print(f"Error processing {os.path.basename(folder)}: {e}")
                error_count += 1
            
            # Print progress
            completed = success_count + error_count
            print(f"Progress: {completed}/{total_folders} ({completed/total_folders*100:.1f}%)")
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print(f"\nMigration completed in {elapsed_time:.2f} seconds!")
    print(f"Successfully imported: {success_count} manga")
    print(f"Failed to import: {error_count} manga")

if __name__ == "__main__":
    main()
