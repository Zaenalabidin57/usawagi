from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, auth
from django.contrib.auth import authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
from django.db.models import Count, Q
from .models import (Category, Actress, Post, PostImage, Comment, UserPermission, 
                   UserProfile, MangaCategory, MangaTag, MangaAuthor, Manga, 
                   DownloadLink, HostType, Contact, Bookmark, ContentType,
                   add_points_for_post, add_points_for_like, add_points_for_comment, 
                   add_points_for_bookmark)
from django.contrib.contenttypes.models import ContentType
import random
from datetime import datetime
from django.core.paginator import Paginator
from django.http import FileResponse

# Create your views here.
def index(request):
    recent_posts = Post.objects.all().order_by('-created_at')[:8]
    recent_mangas = Manga.objects.all().order_by('-created_at')[:8]
    categories = Category.objects.annotate(post_count=Count('posts')).order_by('-post_count')
    
    context = {
        'recent_posts': recent_posts,
        'recent_mangas': recent_mangas,
        'categories': categories,
        'current_year': datetime.now().year
    }
    return render(request, 'index.html', context)

def home(request):
    # Get recent posts, separating official and member posts
    official_posts = Post.objects.filter(is_member_post=False).order_by('-created_at')[:8]
    member_posts = Post.objects.filter(is_member_post=True).order_by('-created_at')[:4]
    recent_mangas = Manga.objects.all().order_by('-created_at')[:4]
    
    context = {
        'official_posts': official_posts,
        'member_posts': member_posts,
        'recent_mangas': recent_mangas,
    }
    return render(request, 'index.html', context)

def blog(request):
    # Get filter parameters
    category = request.GET.get('category')
    search = request.GET.get('search') or request.GET.get('q')  # Support both parameter names
    actress = request.GET.get('actress')
    member_posts = request.GET.get('member_posts')
    
    # Base queryset
    posts = Post.objects.all()
    
    # Apply filters
    if category:
        posts = posts.filter(categories__name=category)
    if search:
        posts = posts.filter(Q(title__icontains=search) | Q(categories__name__icontains=search) | Q(actresses__name__icontains=search)).distinct()
    if actress:
        posts = posts.filter(actresses__name=actress)
    if member_posts:
        posts = posts.filter(is_member_post=True if member_posts == 'true' else False)
    
    # Paginate results
    paginator = Paginator(posts, 9)  # Show 9 posts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all categories for sidebar
    categories = Category.objects.annotate(post_count=Count('posts')).order_by('-post_count')
    
    # Get all actresses for sidebar
    actresses = Actress.objects.annotate(post_count=Count('posts')).order_by('-post_count')
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'actresses': actresses,
        'category': category,
        'search': search,
        'actress': actress,
        'member_posts': member_posts,
    }
    return render(request, 'blog.html', context)

def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)
    comments = Comment.objects.filter(post=post).order_by('-created_at')
    total_comments = comments.count()
    
    # Get content type for post
    post_content_type = ContentType.objects.get_for_model(Post)
    
    # Check if user has bookmarked this post
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = Bookmark.objects.filter(
            user=request.user,
            content_type=post_content_type,
            object_id=post.id
        ).exists()
    
    # Increment view count
    post.views += 1
    post.save(update_fields=['views'])
    
    # Get popular posts for sidebar
    popular_posts = Post.objects.exclude(id=post.id).order_by('-views')[:5]
    
    context = {
        'post': post,
        'comments': comments,
        'total_comments': total_comments,
        'popular_posts': popular_posts,
        'post_content_type_id': post_content_type.id,
        'is_bookmarked': is_bookmarked,
    }
    return render(request, 'post_detail.html', context)

# Helper function to get or create categories from a space-separated string
def process_categories(categories_str):
    if not categories_str:
        return []
    
    category_names = [name.strip() for name in categories_str.split() if name.strip()]
    category_list = []
    
    for name in category_names:
        category, created = Category.objects.get_or_create(name=name)
        category_list.append(category)
    
    return category_list

# Helper function to get or create actresses from a space-separated string
def process_actresses(actresses_str):
    if not actresses_str:
        return []
    
    actress_names = [name.strip() for name in actresses_str.split() if name.strip()]
    actress_list = []
    
    for name in actress_names:
        actress, created = Actress.objects.get_or_create(name=name)
        actress_list.append(actress)
    
    return actress_list

@login_required(login_url='signin')
def create_post(request):
    # Check if user has permission to create posts
    try:
        permission = UserPermission.objects.get(user=request.user)
        if not permission.can_create_posts and not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, "You don't have permission to create posts.")
            return redirect('blog')
    except UserPermission.DoesNotExist:
        # If permission doesn't exist, create it with default values (can create posts)
        UserPermission.objects.create(user=request.user, can_create_posts=True)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        categories_str = request.POST.get('categories')
        actresses_str = request.POST.get('actresses')
        
        # Create a unique slug
        base_slug = slugify(title)
        slug = base_slug
        counter = 1
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Determine if this is a member post based on user's role
        is_member_post = not (request.user.is_staff or request.user.is_superuser)
        
        # Create the post
        post = Post.objects.create(
            title=title,
            slug=slug,
            content="",  # Empty content as we're not using it anymore
            author=request.user,
            is_member_post=is_member_post
        )
        
        # Award points for creating a post
        add_points_for_post(request.user)
        
        # Process categories
        category_list = process_categories(categories_str)
        post.categories.set(category_list)
        
        # Process actresses
        actress_list = process_actresses(actresses_str)
        post.actresses.set(actress_list)
        
        # Process images
        images = request.FILES.getlist('images')
        thumbnail_index = int(request.POST.get('thumbnail_index', 0))
        
        for i, image in enumerate(images):
            is_thumbnail = (i == thumbnail_index)
            PostImage.objects.create(
                post=post,
                image=image,
                is_thumbnail=is_thumbnail,
                order=i
            )
        
        # Process download links
        host_types = request.POST.getlist('download_host_type')
        download_urls = request.POST.getlist('download_url')
        
        for i, (host_type_id, url) in enumerate(zip(host_types, download_urls)):
            if url.strip():  # Only create if URL is not empty
                host_type = HostType.objects.get(id=host_type_id)
                DownloadLink.objects.create(
                    post=post,
                    host_type=host_type,
                    url=url,
                    order=i
                )
        
        messages.success(request, "Post created successfully!")
        return redirect('post_detail', slug=post.slug)
    
    # For GET requests
    host_types = HostType.objects.all()
    return render(request, 'create_post.html', {'host_types': host_types})

@login_required(login_url='signin')
def member_create_post(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        categories_str = request.POST.get('categories')
        actresses_str = request.POST.get('actresses')
        
        # Create a unique slug
        base_slug = slugify(title)
        slug = base_slug
        counter = 1
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Create the post as a member post
        post = Post.objects.create(
            title=title,
            slug=slug,
            content="",  # Empty content as we're not using it anymore
            author=request.user,
            is_member_post=True
        )
        
        # Award points for creating a post
        add_points_for_post(request.user)
        
        # Process categories
        category_list = process_categories(categories_str)
        post.categories.set(category_list)
        
        # Process actresses
        actress_list = process_actresses(actresses_str)
        post.actresses.set(actress_list)
        
        # Process images
        images = request.FILES.getlist('images')
        thumbnail_index = int(request.POST.get('thumbnail_index', 0))
        
        for i, image in enumerate(images):
            is_thumbnail = (i == thumbnail_index)
            PostImage.objects.create(
                post=post,
                image=image,
                is_thumbnail=is_thumbnail,
                order=i
            )
        
        # Process download links
        download_links = request.POST.getlist('download_link')
        
        # Get or create a "downloads" host type
        downloads_host, created = HostType.objects.get_or_create(
            name="Downloads",
            defaults={
                'icon': 'fa-download',
                'color': 'primary'
            }
        )
        
        for i, link in enumerate(download_links):
            if link.strip():
                DownloadLink.objects.create(
                    post=post,
                    host_type=downloads_host,
                    url=link,
                    order=i
                )
        
        messages.success(request, "Post created successfully!")
        return redirect('post_detail', slug=slug)
    
    categories = Category.objects.all()
    actresses = Actress.objects.all()
    
    context = {
        'categories': categories,
        'actresses': actresses,
        'is_member_post': True
    }
    return render(request, 'member_create_post.html', context)

@login_required(login_url='signin')
def edit_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    
    # Only author, staff or superuser can edit
    if post.author != request.user and not request.user.is_staff and not request.user.is_superuser:
        try:
            permission = request.user.permission
            if not permission.can_create_posts:
                messages.error(request, "You don't have permission to edit this post.")
                return redirect('post_detail', slug=post.slug)
        except:
            messages.error(request, "You don't have permission to edit this post.")
            return redirect('post_detail', slug=post.slug)
    
    # Get existing categories as space-separated string
    existing_categories = ' '.join([category.name for category in post.categories.all()])
    
    # Get existing actresses as space-separated string
    existing_actresses = ' '.join([actress.name for actress in post.actresses.all()])
    
    # Get existing images
    existing_images = post.images.all().order_by('order')
    
    # Get existing download links
    existing_links = post.download_links.all().order_by('order')
    
    if request.method == 'POST':
        title = request.POST.get('title')
        categories_str = request.POST.get('categories')
        actresses_str = request.POST.get('actresses')
        
        # Update post
        post.title = title
        post.save()
        
        # Process categories
        category_list = process_categories(categories_str)
        post.categories.set(category_list)
        
        # Process actresses
        actress_list = process_actresses(actresses_str)
        post.actresses.set(actress_list)
        
        # Process images - handle existing and new images
        keep_image_ids = request.POST.getlist('keep_image')
        thumbnail_id = request.POST.get('thumbnail_image', None)
        
        # Delete images that are not in keep_image_ids
        for image in existing_images:
            if str(image.id) not in keep_image_ids:
                image.image.delete()  # Delete the actual file
                image.delete()  # Delete the database record
        
        # Set thumbnail
        if thumbnail_id:
            # First, unset all thumbnails
            post.images.all().update(is_thumbnail=False)
            # Then set the selected one
            try:
                thumbnail = post.images.get(id=thumbnail_id)
                thumbnail.is_thumbnail = True
                thumbnail.save()
            except PostImage.DoesNotExist:
                pass
        
        # Add new images
        new_images = request.FILES.getlist('new_images')
        new_thumbnail_index = request.POST.get('new_thumbnail_index', -1)
        try:
            new_thumbnail_index = int(new_thumbnail_index)
        except ValueError:
            new_thumbnail_index = -1
        
        # Get the highest order value
        highest_order = post.images.aggregate(models.Max('order'))['order__max'] or -1
        
        for i, image_file in enumerate(new_images):
            is_thumbnail = (i == new_thumbnail_index and not thumbnail_id)
            PostImage.objects.create(
                post=post,
                image=image_file,
                is_thumbnail=is_thumbnail,
                order=highest_order + i + 1
            )
        
        # Process download links
        # First, delete all existing links
        post.download_links.all().delete()
        
        # Then create new ones from the form
        host_types = request.POST.getlist('download_host_type')
        download_urls = request.POST.getlist('download_url')
        
        for i, (host_type_id, url) in enumerate(zip(host_types, download_urls)):
            if url.strip():  # Only create if URL is not empty
                try:
                    host_type = HostType.objects.get(id=host_type_id)
                    DownloadLink.objects.create(
                        post=post,
                        host_type=host_type,
                        url=url,
                        order=i
                    )
                except HostType.DoesNotExist:
                    pass  # Skip if host type doesn't exist
        
        messages.success(request, "Post updated successfully!")
        return redirect('post_detail', slug=post.slug)
    
    # For GET requests
    host_types = HostType.objects.all()
    context = {
        'post': post,
        'existing_categories': existing_categories,
        'existing_actresses': existing_actresses,
        'existing_images': existing_images,
        'existing_links': existing_links,
        'host_types': host_types,
    }
    return render(request, 'edit_post.html', context)

@login_required(login_url='signin')
def delete_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    
    # Check if user has permission to delete posts (either the author, staff, or has permission)
    if not (request.user == post.author or request.user.is_staff or request.user.is_superuser):
        try:
            permission = request.user.permission
            if not permission.can_create_posts:
                messages.error(request, "You don't have permission to delete posts.")
                return redirect('blog')
        except:
            messages.error(request, "You don't have permission to delete posts.")
            return redirect('blog')
    
    if request.method == 'POST':
        post.delete()
        messages.success(request, "Post deleted successfully")
        return redirect('profile', username=request.user.username)
    
    context = {
        'post': post,
    }
    return render(request, 'delete_post.html', context)

@login_required(login_url='signin')
def delete_image(request, image_id):
    image = get_object_or_404(PostImage, id=image_id)
    post = image.post
    
    # Make sure the user is the author of the post
    if request.user != post.author:
        messages.error(request, "You don't have permission to delete this image")
        return redirect('post_detail', slug=post.slug)
    
    # Check if this is the only image or if it's the thumbnail
    is_thumbnail = image.is_thumbnail
    post_images = post.images.all()
    
    if post_images.count() == 1:
        messages.error(request, "You cannot delete the only image of a post")
        return redirect('edit_post', slug=post.slug)
    
    # Delete the image
    image.delete()
    
    # If the deleted image was the thumbnail, set the first remaining image as thumbnail
    if is_thumbnail and post_images.exists():
        new_thumbnail = post_images.first()
        new_thumbnail.is_thumbnail = True
        new_thumbnail.save()
    
    messages.success(request, "Image deleted successfully")
    return redirect('edit_post', slug=post.slug)

@login_required(login_url='signin')
def like_post(request, slug):
    if request.method == 'POST':
        post = get_object_or_404(Post, slug=slug)
        post.likes += 1
        post.save()
        
        # Award points to the post author for receiving a like
        add_points_for_like(post)
        
    return redirect('post_detail', slug=slug)

@login_required(login_url='signin')
def add_comment(request, slug):
    post = get_object_or_404(Post, slug=slug)
    
    if request.method == 'POST':
        content = request.POST.get('content')
        Comment.objects.create(
            post=post,
            author=request.user,
            content=content
        )
        
        # Award points to the post author for receiving a comment
        add_points_for_comment(post)
        
    return redirect('post_detail', slug=slug)

@login_required(login_url='signin')
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    post_slug = comment.post.slug
    comment.delete()
    return redirect('post_detail', slug=post_slug)

def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=profile_user).order_by('-created_at')
    mangas = Manga.objects.filter(user=profile_user).order_by('-created_at')
    
    context = {
        'profile_user': profile_user,
        'posts': posts,
        'mangas': mangas,
    }
    return render(request, 'profile.html', context)

@login_required(login_url='signin')
def edit_profile(request):
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        bio = request.POST.get('bio', '')
        
        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            profile_picture = request.FILES['profile_picture']
            profile.profile_picture = profile_picture
        
        # Update user information
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        
        # Update profile information
        profile.bio = bio
        profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile', username=user.username)
    
    context = {
        'profile': profile
    }
    return render(request, 'edit_profile.html', context)

def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        if password == password2:
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists")
                return redirect('signup')
            if User.objects.filter(email=email).exists():
                messages.error(request, "Email already exists")
                return redirect('signup')
            
            User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, "Account created successfully! Please sign in.")
            return redirect('signin')
        else:
            messages.error(request, "Passwords do not match")
            return redirect('signup')
    
    return render(request, 'signup.html')

def signin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth.login(request, user)
            return redirect('index')
        else:
            messages.error(request, "Invalid username or password")
            return redirect('signin')
    
    return render(request, 'signin.html')

@login_required(login_url='signin')
def signout(request):
    auth.logout(request)
    return redirect('index')

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        Contact.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        
        messages.success(request, f"Thank you, {name}! Your message has been sent.")
        return redirect('contact')
    
    return render(request, 'contact.html')

# API endpoint for category autocomplete
def get_categories(request):
    from django.http import JsonResponse
    
    query = request.GET.get('q', '')
    if query:
        categories = Category.objects.filter(name__icontains=query).values_list('name', flat=True)[:10]
    else:
        categories = Category.objects.annotate(post_count=Count('posts')).order_by('-post_count').values_list('name', flat=True)[:10]
    
    return JsonResponse(list(categories), safe=False)

def random_post(request):
    post_count = Post.objects.count()
    manga_count = Manga.objects.count()
    total_count = post_count + manga_count
    
    if total_count > 0:
        # Randomly decide whether to show a post or manga
        random_index = random.randint(0, total_count - 1)
        
        if random_index < post_count:
            # Show a random post
            random_post = Post.objects.all()[random_index]
            return redirect('post_detail', slug=random_post.slug)
        else:
            # Show a random manga
            manga_index = random_index - post_count
            random_manga = Manga.objects.all()[manga_index]
            return redirect('manga_detail', slug=random_manga.slug)
    else:
        messages.info(request, "No content available yet.")
        return redirect('blog')

# Manga views
def manga_list(request):
    mangas = Manga.objects.all().order_by('-created_at')
    
    # Get filter parameters
    category = request.GET.get('category')
    tag = request.GET.get('tag')
    author = request.GET.get('author')
    search = request.GET.get('search') or request.GET.get('q')  # Support both parameter names
    
    # Apply filters if provided
    if category:
        mangas = mangas.filter(manga_categories__name=category)
    
    if tag:
        mangas = mangas.filter(manga_tags__name=tag)
    
    if author:
        mangas = mangas.filter(manga_authors__name=author)
    
    if search:
        mangas = mangas.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(manga_categories__name__icontains=search) |
            Q(manga_tags__name__icontains=search) |
            Q(manga_authors__name__icontains=search)
        ).distinct()
    
    # Pagination
    paginator = Paginator(mangas, 12)  # 12 mangas per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all categories and tags for sidebar
    categories = MangaCategory.objects.annotate(manga_count=Count('mangas')).order_by('-manga_count')
    tags = MangaTag.objects.annotate(manga_count=Count('mangas')).order_by('-manga_count')[:20]  # Top 20 tags
    authors = MangaAuthor.objects.annotate(manga_count=Count('mangas')).order_by('-manga_count')
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'tags': tags,
        'authors': authors,
        'category': category,
        'tag': tag,
        'author': author,
        'search': search,
    }
    return render(request, 'manga_list.html', context)

def manga_detail(request, slug):
    manga = get_object_or_404(Manga, slug=slug)
    
    # Get content type for manga
    manga_content_type = ContentType.objects.get_for_model(Manga)
    
    # Check if user has bookmarked this manga
    is_bookmarked = False
    if request.user.is_authenticated:
        is_bookmarked = Bookmark.objects.filter(
            user=request.user,
            content_type=manga_content_type,
            object_id=manga.id
        ).exists()
    
    # Increment view count
    manga.views += 1
    manga.save(update_fields=['views'])
    
    # Get related manga based on categories
    related_manga = Manga.objects.filter(
        manga_categories__in=manga.manga_categories.all()
    ).exclude(id=manga.id).distinct()[:4]
    
    context = {
        'manga': manga,
        'related_manga': related_manga,
        'manga_content_type_id': manga_content_type.id,
        'is_bookmarked': is_bookmarked,
    }
    return render(request, 'manga_detail.html', context)

def manga_view(request, slug):
    manga = get_object_or_404(Manga, slug=slug)
    
    # Extract PDF pages as images
    import tempfile
    import os
    from pdf2image import convert_from_path
    from django.conf import settings
    import time
    
    # Create a directory for manga pages if it doesn't exist
    manga_pages_dir = os.path.join(settings.MEDIA_ROOT, 'manga_pages', slug)
    os.makedirs(manga_pages_dir, exist_ok=True)
    
    # Path to store the extracted images
    images_path = os.path.join('manga_pages', slug)
    
    # Check if pages have already been extracted
    existing_pages = [f for f in os.listdir(manga_pages_dir) if f.endswith('.jpg')]
    
    # If no pages exist, extract them
    pages = []
    if not existing_pages:
        try:
            # Create a temporary file to store the PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                for chunk in manga.pdf_file.chunks():
                    temp_file.write(chunk)
            
            # Convert PDF to images
            pdf_images = convert_from_path(temp_file.name, dpi=150)
            
            # Save each page as an image
            for i, img in enumerate(pdf_images):
                page_filename = f'page_{i+1}.jpg'
                page_path = os.path.join(manga_pages_dir, page_filename)
                img.save(page_path, 'JPEG', quality=85)
                pages.append(os.path.join(settings.MEDIA_URL, images_path, page_filename))
            
            # Clean up the temporary file
            os.unlink(temp_file.name)
        except Exception as e:
            print(f"Error extracting PDF pages: {e}")
    else:
        # Use existing pages
        existing_pages.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))
        for page in existing_pages:
            pages.append(os.path.join(settings.MEDIA_URL, images_path, page))
    
    context = {
        'manga': manga,
        'pages': pages,
    }
    return render(request, 'manga_view.html', context)

def manga_download(request, slug):
    manga = get_object_or_404(Manga, slug=slug)
    
    # Increment download count if tracked
    if hasattr(manga, 'download_shortlink') and manga.download_shortlink:
        manga.download_shortlink.clicks += 1
        manga.download_shortlink.save(update_fields=['clicks'])
    
    # Serve the file for download
    response = FileResponse(manga.pdf_file, as_attachment=True, filename=f"{manga.slug}.pdf")
    return response

@login_required(login_url='signin')
def create_manga(request):
    # Check if user has permission to create posts
    try:
        permission = UserPermission.objects.get(user=request.user)
        if not permission.can_create_posts and not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, "You don't have permission to create manga posts.")
            return redirect('manga_list')
    except UserPermission.DoesNotExist:
        # If permission doesn't exist, create it with default values (can create posts)
        UserPermission.objects.create(user=request.user, can_create_posts=True)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        tags_str = request.POST.get('manga_tags')
        authors_str = request.POST.get('manga_authors')
        
        # Create a unique slug from the title
        base_slug = slugify(title)
        slug = base_slug
        counter = 1
        while Manga.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Handle PDF file upload
        pdf_file = request.FILES.get('pdf_file')
        if not pdf_file:
            messages.error(request, "PDF file is required.")
            return redirect('create_manga')
        
        # Handle thumbnail upload (optional)
        thumbnail = request.FILES.get('thumbnail')
        
        # Create the manga
        manga = Manga.objects.create(
            title=title,
            slug=slug,
            description=description,
            pdf_file=pdf_file,
            thumbnail=thumbnail,
            user=request.user
        )
        
        # Award points for creating a manga (same as for post)
        add_points_for_post(request.user)
        
        # Process tags
        if tags_str:
            tag_names = [name.strip() for name in tags_str.split() if name.strip()]
            for name in tag_names:
                tag, created = MangaTag.objects.get_or_create(name=name)
                manga.manga_tags.add(tag)
        
        # Process authors
        if authors_str:
            author_names = [name.strip() for name in authors_str.split() if name.strip()]
            for name in author_names:
                author, created = MangaAuthor.objects.get_or_create(name=name)
                manga.manga_authors.add(author)
        
        # If no thumbnail was provided, generate one from the first page of the PDF
        if not thumbnail:
            try:
                import tempfile
                import os
                from pdf2image import convert_from_path
                from django.core.files.base import ContentFile
                import io
                from PIL import Image
                
                # Create a temporary file to store the PDF
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    for chunk in pdf_file.chunks():
                        temp_file.write(chunk)
                
                # Extract the first page as an image
                try:
                    # Convert first page of PDF to image
                    images = convert_from_path(temp_file.name, first_page=1, last_page=1)
                    if images:
                        # Get the first page
                        img = images[0]
                        # Resize if needed
                        img = img.resize((800, int(800 * img.height / img.width)), Image.LANCZOS)
                        
                        # Save the image to the manga's thumbnail field
                        buffer = io.BytesIO()
                        img.save(buffer, format='JPEG', quality=85)
                        manga.thumbnail.save(f"{slug}_thumbnail.jpg", ContentFile(buffer.getvalue()))
                except Exception as e:
                    print(f"Error generating thumbnail: {e}")
                
                # Clean up the temporary file
                os.unlink(temp_file.name)
            except Exception as e:
                print(f"Error handling PDF for thumbnail generation: {e}")
        
        messages.success(request, "Manga uploaded successfully!")
        return redirect('manga_detail', slug=manga.slug)
    
    # GET request - show the form
    host_types = HostType.objects.all()
    context = {
        'host_types': host_types,
    }
    return render(request, 'create_manga.html', context)

@login_required(login_url='signin')
def edit_manga(request, slug):
    manga = get_object_or_404(Manga, slug=slug)
    
    # Check if user is authorized to edit this manga
    if request.user != manga.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to edit this manga.")
        return redirect('manga_detail', slug=manga.slug)
    
    # Get existing values for pre-filling the form
    existing_tags = ' '.join([tag.name for tag in manga.manga_tags.all()])
    existing_authors = ' '.join([author.name for author in manga.manga_authors.all()])
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        tags_str = request.POST.get('manga_tags')
        authors_str = request.POST.get('manga_authors')
        
        # Update the manga
        manga.title = title
        manga.description = description
        
        # Handle PDF file upload if provided
        pdf_file = request.FILES.get('pdf_file')
        if pdf_file:
            # Delete the old PDF file if it exists
            if manga.pdf_file:
                manga.pdf_file.delete(save=False)
            manga.pdf_file = pdf_file
        
        # Handle thumbnail upload if provided
        thumbnail = request.FILES.get('thumbnail')
        if thumbnail:
            # Delete the old thumbnail if it exists
            if manga.thumbnail:
                manga.thumbnail.delete(save=False)
            manga.thumbnail = thumbnail
        
        manga.save()
        
        # Process tags
        manga.manga_tags.clear()
        if tags_str:
            tag_names = [name.strip() for name in tags_str.split() if name.strip()]
            for name in tag_names:
                tag, created = MangaTag.objects.get_or_create(name=name)
                manga.manga_tags.add(tag)
        
        # Process authors
        manga.manga_authors.clear()
        if authors_str:
            author_names = [name.strip() for name in authors_str.split() if name.strip()]
            for name in author_names:
                author, created = MangaAuthor.objects.get_or_create(name=name)
                manga.manga_authors.add(author)
        
        messages.success(request, "Manga updated successfully!")
        return redirect('manga_detail', slug=manga.slug)
    
    # For GET requests
    context = {
        'manga': manga,
        'existing_tags': existing_tags,
        'existing_authors': existing_authors,
    }
    return render(request, 'edit_manga.html', context)

@login_required(login_url='signin')
def delete_manga(request, slug):
    manga = get_object_or_404(Manga, slug=slug)
    
    # Only author, staff or superuser can delete
    if manga.user != request.user and not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, "You don't have permission to delete this manga.")
        return redirect('manga_detail', slug=manga.slug)
    
    if request.method == 'POST':
        # Delete the PDF file
        if manga.pdf_file:
            manga.pdf_file.delete(save=False)
        
        # Delete the thumbnail
        if manga.thumbnail:
            manga.thumbnail.delete(save=False)
        
        # Delete the shortlink if it exists
        if manga.download_shortlink:
            manga.download_shortlink.delete()
        
        # Delete the manga
        manga.delete()
        
        messages.success(request, "Manga deleted successfully!")
        return redirect('manga_list')
    
    return render(request, 'delete_manga.html', {'manga': manga})

def like_manga(request, slug):
    manga = get_object_or_404(Manga, slug=slug)
    manga.likes += 1
    manga.save(update_fields=['likes'])
    
    # Award points to the manga creator for receiving a like
    if manga.user and hasattr(manga.user, 'profile'):
        manga.user.profile.points += 1  # Using POINT_FOR_LIKE value
        manga.user.profile.save()
        
    return redirect('manga_detail', slug=slug)

@login_required
def bookmark_item(request):
    if request.method == 'POST':
        content_type_id = request.POST.get('content_type_id')
        object_id = request.POST.get('object_id')
        
        # Get the content type and model
        content_type = ContentType.objects.get(id=content_type_id)
        model_class = content_type.model_class()
        item = model_class.objects.get(id=object_id)
        
        # Check if bookmark already exists
        bookmark, created = Bookmark.objects.get_or_create(
            user=request.user,
            content_type=content_type,
            object_id=object_id
        )
        
        if created:
            message = f"Added to your bookmarks!"
            # Award points to the content author for being bookmarked
            add_points_for_bookmark(item)
        else:
            message = f"Already in your bookmarks!"
            
        # Redirect back to the item's page
        if content_type.model == 'post':
            return redirect('post_detail', slug=item.slug)
        elif content_type.model == 'manga':
            return redirect('manga_detail', slug=item.slug)
        else:
            return redirect('home')
    
    return redirect('home')

@login_required
def remove_bookmark(request, bookmark_id):
    bookmark = get_object_or_404(Bookmark, id=bookmark_id, user=request.user)
    bookmark.delete()
    
    # Redirect back to the bookmarks page
    return redirect('user_bookmarks', username=request.user.username)

def user_bookmarks(request, username):
    profile_user = get_object_or_404(User, username=username)
    bookmarks = Bookmark.objects.filter(user=profile_user)
    
    # Separate bookmarks by type
    post_bookmarks = [b for b in bookmarks if b.content_type.model == 'post']
    manga_bookmarks = [b for b in bookmarks if b.content_type.model == 'manga']
    
    context = {
        'profile_user': profile_user,
        'post_bookmarks': post_bookmarks,
        'manga_bookmarks': manga_bookmarks,
    }
    
    return render(request, 'bookmarks.html', context)

@login_required(login_url='signin')
def member_create_manga(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        tags_str = request.POST.get('manga_tags')
        authors_str = request.POST.get('manga_authors')
        
        # Create a unique slug from the title
        base_slug = slugify(title)
        slug = base_slug
        counter = 1
        while Manga.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Handle PDF file upload
        pdf_file = request.FILES.get('pdf_file')
        if not pdf_file:
            messages.error(request, "PDF file is required.")
            return redirect('member_create_manga')
        
        # Handle thumbnail upload (optional)
        thumbnail = request.FILES.get('thumbnail')
        
        # Create the manga
        manga = Manga.objects.create(
            title=title,
            slug=slug,
            description=description,
            pdf_file=pdf_file,
            thumbnail=thumbnail,
            user=request.user
        )
        
        # Award points for creating a manga (same as for post)
        add_points_for_post(request.user)
        
        # Process tags
        if tags_str:
            tag_names = [name.strip() for name in tags_str.split() if name.strip()]
            for name in tag_names:
                tag, created = MangaTag.objects.get_or_create(name=name)
                manga.manga_tags.add(tag)
        
        # Process authors
        if authors_str:
            author_names = [name.strip() for name in authors_str.split() if name.strip()]
            for name in author_names:
                author, created = MangaAuthor.objects.get_or_create(name=name)
                manga.manga_authors.add(author)
        
        # Process categories
        categories = request.POST.getlist('manga_categories')
        for category_id in categories:
            try:
                category = MangaCategory.objects.get(id=category_id)
                manga.manga_categories.add(category)
            except MangaCategory.DoesNotExist:
                pass
        
        # Create shortlink for downloads
        shortlink = ShortLink.objects.create(
            original_url=f"/manga/download/{slug}/",
            clicks=0
        )
        manga.download_shortlink = shortlink
        manga.save()
        
        messages.success(request, "Manga created successfully!")
        return redirect('manga_detail', slug=slug)
    
    categories = MangaCategory.objects.all()
    tags = MangaTag.objects.all()
    authors = MangaAuthor.objects.all()
    
    context = {
        'categories': categories,
        'tags': tags,
        'authors': authors,
        'is_member_manga': True
    }
    return render(request, 'member_create_manga.html', context)
