from django.contrib import admin
from .models import Post, Comment, Contact, Category, PostImage, UserPermission, HostType, DownloadLink, Actress

# Register your models here.
class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 1

class DownloadLinkInline(admin.TabularInline):
    model = DownloadLink
    extra = 1

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'get_categories', 'get_actresses', 'author', 'created_at', 'likes', 'views')
    list_filter = ('created_at', 'categories', 'actresses')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [PostImageInline, DownloadLinkInline]
    filter_horizontal = ('categories', 'actresses')
    
    def get_categories(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])
    get_categories.short_description = 'Categories'
    
    def get_actresses(self, obj):
        return ", ".join([a.name for a in obj.actresses.all()])
    get_actresses.short_description = 'Actresses'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'post_count')
    search_fields = ('name',)
    
    def post_count(self, obj):
        return obj.posts.count()
    post_count.short_description = 'Posts'

@admin.register(Actress)
class ActressAdmin(admin.ModelAdmin):
    list_display = ('name', 'post_count')
    search_fields = ('name',)
    
    def post_count(self, obj):
        return obj.posts.count()
    post_count.short_description = 'Posts'

@admin.register(HostType)
class HostTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'icon')
    search_fields = ('name',)

@admin.register(DownloadLink)
class DownloadLinkAdmin(admin.ModelAdmin):
    list_display = ('post', 'host_type', 'url', 'order')
    list_filter = ('host_type',)
    search_fields = ('post__title', 'url')

@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ('post', 'image', 'is_thumbnail', 'order')
    list_filter = ('is_thumbnail',)
    search_fields = ('post__title',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content',)

@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'can_create_posts')
    list_filter = ('can_create_posts',)
    search_fields = ('user__username',)
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of permission objects
        return False

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'subject', 'message')
