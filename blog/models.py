from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from django.db.models.signals import post_save
from django.dispatch import receiver
from PIL import Image
import os
from io import BytesIO
from django.core.files.base import ContentFile
from shortlink.models import ShortLink

# Create your models here.

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Categories'

class Actress(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Actresses'

class HostType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class", blank=True)
    color = models.CharField(max_length=20, default="primary", help_text="Button color class (primary, secondary, accent, etc.)")
    
    def __str__(self):
        return self.name

class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    categories = models.ManyToManyField(Category, related_name='posts')
    actresses = models.ManyToManyField(Actress, related_name='posts', blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.IntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    
    def __str__(self):
        return self.title
    
    def get_thumbnail(self):
        # First try to get an image marked as thumbnail
        thumbnail = self.images.filter(is_thumbnail=True).first()
        # If no image is marked as thumbnail, get the first image
        if not thumbnail:
            thumbnail = self.images.first()
        return thumbnail
    
    class Meta:
        ordering = ['-created_at']

class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='post_images/')
    thumbnail = models.ImageField(upload_to='post_thumbnails/', blank=True, null=True)
    is_thumbnail = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        # Generate thumbnail when saving the image
        if not self.thumbnail and self.image:
            # Open the uploaded image
            img = Image.open(self.image)
            
            # Calculate the aspect ratio
            width, height = img.size
            aspect_ratio = width / height
            
            # Set the thumbnail size (max width 800px, maintaining aspect ratio)
            thumb_width = 800
            thumb_height = int(thumb_width / aspect_ratio)
            
            # Resize the image
            img.thumbnail((thumb_width, thumb_height), Image.Resampling.LANCZOS)
            
            # Save the thumbnail to a BytesIO object
            thumb_io = BytesIO()
            img_format = 'JPEG' if self.image.name.lower().endswith(('.jpg', '.jpeg')) else 'PNG'
            img.save(thumb_io, format=img_format, quality=85)
            
            # Generate a thumbnail filename
            filename = os.path.basename(self.image.name)
            name, ext = os.path.splitext(filename)
            thumb_filename = f"{name}_thumb{ext}"
            
            # Save the thumbnail to the thumbnail field
            self.thumbnail.save(thumb_filename, ContentFile(thumb_io.getvalue()), save=False)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Image for {self.post.title}"
    
    class Meta:
        ordering = ['order']

class DownloadLink(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='download_links')
    host_type = models.ForeignKey(HostType, on_delete=models.CASCADE)
    url = models.URLField()
    short_link = models.OneToOneField(ShortLink, on_delete=models.CASCADE, null=True, blank=True, related_name='download_link')
    order = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.host_type.name} link for {self.post.title}"
    
    def save(self, *args, **kwargs):
        # Create a shortlink if one doesn't exist
        if not self.short_link and self.url:
            short_link = ShortLink.objects.create(
                original_url=self.url,
                title=f"{self.host_type.name} - {self.post.title}",
                description=f"Download link for {self.post.title} via {self.host_type.name}",
                creator=self.post.author
            )
            self.short_link = short_link
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        if self.short_link:
            return f"/s/{self.short_link.short_code}/"
        return self.url
    
    class Meta:
        ordering = ['order']

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.author.username} on {self.post.title}"
    
    class Meta:
        ordering = ['-created_at']

class UserPermission(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='permission')
    can_create_posts = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username}'s permissions"

class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.subject

# Signal to create user permission when a new user is created
@receiver(post_save, sender=User)
def create_user_permission(sender, instance, created, **kwargs):
    if created:
        UserPermission.objects.create(user=instance, can_create_posts=False)

# Connect the signal
post_save.connect(create_user_permission, sender=User)
