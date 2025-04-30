from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from django.db.models.signals import post_save
from django.dispatch import receiver
import os
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from shortlink.models import ShortLink
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

# Create your models here.

# Point system constants
POINT_FOR_POST = 10
POINT_FOR_LIKE = 1
POINT_FOR_COMMENT = 2
POINT_FOR_BOOKMARK = 5

# Helper functions for point system
def add_points_for_post(user):
    """Add points to user for creating a post"""
    if user and hasattr(user, 'profile'):
        user.profile.points += POINT_FOR_POST
        user.profile.save()

def add_points_for_like(post):
    """Add points to post author when post is liked"""
    if post and post.author and hasattr(post.author, 'profile'):
        post.author.profile.points += POINT_FOR_LIKE
        post.author.profile.save()

def add_points_for_comment(post):
    """Add points to post author when post receives a comment"""
    if post and post.author and hasattr(post.author, 'profile'):
        post.author.profile.points += POINT_FOR_COMMENT
        post.author.profile.save()

def add_points_for_bookmark(content_object):
    """Add points to content author when content is bookmarked"""
    # Check if it's a Post or Manga
    if hasattr(content_object, 'author') and hasattr(content_object.author, 'profile'):
        content_object.author.profile.points += POINT_FOR_BOOKMARK
        content_object.author.profile.save()
    elif hasattr(content_object, 'user') and hasattr(content_object.user, 'profile'):
        content_object.user.profile.points += POINT_FOR_BOOKMARK
        content_object.user.profile.save()

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

    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Manga Categories'

class MangaTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Manga Tags'

class MangaAuthor(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = 'Manga Authors'

class HostType(models.Model):
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class", blank=True)
    color = models.CharField(max_length=20, default="primary", help_text="Button color class (primary, secondary, accent, etc.)")
    
    def __str__(self):
        return self.name

class Manga(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    manga_tags = models.ManyToManyField(MangaTag, related_name='mangas')
    manga_authors = models.ManyToManyField(MangaAuthor, related_name='mangas')
    description = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to='manga/pdfs/')
    thumbnail = models.ImageField(upload_to='manga/thumbnails/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.IntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mangas', null=True, default=None)
    download_shortlink = models.OneToOneField(ShortLink, on_delete=models.SET_NULL, null=True, blank=True, related_name='manga_download')
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Create a new manga
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Generate shortlink for PDF download if it doesn't exist
        if is_new or not self.download_shortlink:
            from shortlink.models import ShortLink
            shortlink = ShortLink.objects.create(
                original_url=f"/manga/download/{self.slug}/",
                title=f"Download {self.title}"
            )
            self.download_shortlink = shortlink
            super().save(update_fields=['download_shortlink'])
    
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('manga_detail', kwargs={'slug': self.slug})
    
    def get_download_url(self):
        from django.urls import reverse
        if self.download_shortlink:
            return reverse('redirect_to_original', kwargs={'short_code': self.download_shortlink.short_code})
        return reverse('manga_download', kwargs={'slug': self.slug})
    
    def get_view_url(self):
        from django.urls import reverse
        return reverse('manga_view', kwargs={'slug': self.slug})
    
    class Meta:
        ordering = ['-created_at']

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
    is_member_post = models.BooleanField(default=False, help_text="Check if this is a member-created post rather than an official post")
    
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

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    bio = models.TextField(blank=True)
    points = models.PositiveIntegerField(default=0, help_text="Points earned from user interactions with posts")
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.subject

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'content_type', 'object_id')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} bookmarked {self.content_object}"

# Signal to create user permission when a new user is created
@receiver(post_save, sender=User)
def create_user_permission(sender, instance, created, **kwargs):
    if created:
        UserPermission.objects.create(user=instance)

# Signal to create user profile when a new user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

# Connect the signals
post_save.connect(create_user_permission, sender=User)
post_save.connect(create_user_profile, sender=User)
