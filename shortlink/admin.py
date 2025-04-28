from django.contrib import admin
from .models import ShortLink

# Register your models here.

@admin.register(ShortLink)
class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ('short_code', 'original_url', 'title', 'clicks', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('short_code', 'original_url', 'title')
    readonly_fields = ('clicks', 'created_at')
