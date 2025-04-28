from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, auth
from django.contrib.auth import authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.text import slugify
from django.db.models import Count, Q
from .models import Post, Comment, Contact, Category, PostImage, UserPermission, HostType, DownloadLink, Actress
import random
from datetime import datetime
from django.core.paginator import Paginator

# Create your views here.
def index(request):
    recent_posts = Post.objects.all().order_by('-created_at')[:8]
    categories = Category.objects.annotate(post_count=Count('posts')).order_by('-post_count')
    
    context = {
        'recent_posts': recent_posts,
        'categories': categories,
        'current_year': datetime.now().year
    }
    return render(request, 'index.html', context)

def blog(request):
    posts = Post.objects.all().order_by('-created_at')
    
    # Get filter parameters
    category = request.GET.get('category')
    search = request.GET.get('search') or request.GET.get('q')  # Support both parameter names
    actress = request.GET.get('actress')
    
    # Apply filters if provided
    if category:
        posts = posts.filter(categories__name=category)
    
    if actress:
        posts = posts.filter(actresses__name=actress)
    
    if search:
        posts = posts.filter(
            Q(title__icontains=search) |
            Q(categories__name__icontains=search) |
            Q(actresses__name__icontains=search)
        ).distinct()
    
    # Pagination
    paginator = Paginator(posts, 9)  # 9 posts per page
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
    }
    return render(request, 'blog.html', context)

def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)
    comments = post.comments.all()
    recent_posts = Post.objects.exclude(id=post.id)[:3]
    
    # Increment the view counter
    post.views += 1
    post.save(update_fields=['views'])
    
    context = {
        'post': post,
        'comments': comments,
        'recent_posts': recent_posts,
        'total_comments': comments.count(),
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
        
        # Create the post
        post = Post.objects.create(
            title=title,
            slug=slug,
            content="",  # Empty content as we're not using it anymore
            author=request.user
        )
        
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
    return redirect('post_detail', slug=slug)

@login_required(login_url='signin')
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    post_slug = comment.post.slug
    comment.delete()
    return redirect('post_detail', slug=post_slug)

def profile(request, username):
    user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=user)
    
    context = {
        'profile_user': user,
        'posts': posts,
    }
    return render(request, 'profile.html', context)

@login_required(login_url='signin')
def edit_profile(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        
        return redirect('profile', username=user.username)
    
    return render(request, 'edit_profile.html')

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
    """View to redirect to a random blog post"""
    posts = Post.objects.all()
    if posts.exists():
        # Get a random post
        random_post = random.choice(posts)
        return redirect('post_detail', slug=random_post.slug)
    else:
        # If no posts exist, redirect to blog page
        messages.info(request, "No posts available yet!")
        return redirect('blog')
