from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage
import requests
import os
import json
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)


class MediaStorage(S3Boto3Storage):
    """
    Custom storage backend for media files.
    In production, this will use S3 or a similar service.
    """
    location = 'media'
    file_overwrite = False


class MediaServerStorage:
    """
    Storage backend that uses the custom media server API.
    """
    def __init__(self):
        self.media_server_url = os.environ.get('MEDIA_SERVER_URL', 'http://202.10.40.32:8080')
        self.api_key = os.environ.get('MEDIA_SERVER_API_KEY', '')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}' if self.api_key else ''
        }
    
    def _save(self, name, content):
        """
        Save a file to the media server.
        """
        try:
            # Extract file path components
            path_parts = name.split('/')
            file_name = path_parts[-1]
            directory = '/'.join(path_parts[:-1])
            
            # Determine the endpoint based on the file path
            if 'manga_pages' in directory:
                # This is a manga PDF file that needs extraction
                slug = path_parts[-2] if len(path_parts) > 1 else file_name.split('.')[0]
                
                files = {'file': (file_name, content, 'application/pdf')}
                data = {'slug': slug}
                
                response = requests.post(
                    f"{self.media_server_url}/upload/manga/",
                    files=files,
                    data=data,
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Error uploading manga PDF: {response.text}")
                    raise Exception(f"Error uploading manga PDF: {response.text}")
                
                result = response.json()
                logger.info(f"Successfully uploaded manga PDF: {result}")
                
                # Return the path to the first page as a reference
                return result['page_paths'][0] if result['page_paths'] else name
                
            elif 'post_thumbnails' in directory:
                # This is a post thumbnail
                post_id = file_name.split('_')[0]
                
                files = {'file': (file_name, content, 'image/jpeg')}
                data = {'post_id': post_id}
                
                response = requests.post(
                    f"{self.media_server_url}/upload/post-thumbnail/",
                    files=files,
                    data=data,
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Error uploading post thumbnail: {response.text}")
                    raise Exception(f"Error uploading post thumbnail: {response.text}")
                
                result = response.json()
                return result['thumbnail_path']
            
            else:
                # Generic file upload - not implemented yet
                # For now, we'll just return the name as if it was saved
                logger.warning(f"Generic file upload not implemented for: {name}")
                return name
                
        except Exception as e:
            logger.error(f"Error saving file to media server: {str(e)}")
            # Fall back to returning the name as if it was saved
            return name
    
    def url(self, name):
        """
        Return the URL for accessing the file.
        """
        # If the name already starts with http, it's already a full URL
        if name.startswith('http'):
            return name
            
        # Otherwise, construct the URL from the media server base URL
        return f"{self.media_server_url}{name}"
    
    def exists(self, name):
        """
        Check if a file exists on the media server.
        For now, we'll assume it exists to avoid unnecessary API calls.
        """
        return True
    
    def delete(self, name):
        """
        Delete a file from the media server.
        """
        try:
            # For manga files, we need to extract the slug
            if 'manga_pages' in name:
                parts = name.split('/')
                if len(parts) >= 3:
                    slug = parts[-2]  # Extract slug from path
                    
                    response = requests.delete(
                        f"{self.media_server_url}/manga/{slug}",
                        headers=self.headers
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Error deleting manga: {response.text}")
                    
                    return
            
            # For other files, deletion is not implemented yet
            logger.warning(f"Deletion not implemented for: {name}")
            
        except Exception as e:
            logger.error(f"Error deleting file from media server: {str(e)}")


class SelectiveStorage:
    """
    Storage backend that selects between local storage, remote storage,
    and media server storage based on the environment and file type.
    """
    def __init__(self):
        self.local_storage = FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)
        self.remote_storage = MediaStorage()
        self.media_server_storage = MediaServerStorage()
    
    def __getattr__(self, name):
        # Check if we're in development mode
        if settings.DEBUG:
            # In development, use local storage for everything except PDF files
            if hasattr(self, '_name') and self._name and self._name.endswith('.pdf'):
                return getattr(self.media_server_storage, name)
            return getattr(self.local_storage, name)
        
        # In production, use media server for PDFs and specific file types
        if hasattr(self, '_name') and self._name:
            if self._name.endswith('.pdf') or 'manga_pages' in self._name or 'post_thumbnails' in self._name:
                return getattr(self.media_server_storage, name)
        
        # For other files in production, use S3 or similar storage
        return getattr(self.remote_storage, name)
    
    def _save(self, name, content):
        self._name = name  # Store the name for later use in __getattr__
        
        # Delegate to the appropriate storage backend
        if settings.DEBUG:
            if name.endswith('.pdf') or 'manga_pages' in name:
                return self.media_server_storage._save(name, content)
            return self.local_storage._save(name, content)
        
        if name.endswith('.pdf') or 'manga_pages' in name or 'post_thumbnails' in name:
            return self.media_server_storage._save(name, content)
        
        return self.remote_storage._save(name, content)
