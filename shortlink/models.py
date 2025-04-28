from django.db import models
from django.utils.crypto import get_random_string
from django.contrib.auth.models import User

# Create your models here.

class ShortLink(models.Model):
    original_url = models.URLField(max_length=2000)
    short_code = models.CharField(max_length=10, unique=True, db_index=True, blank=True)
    title = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    clicks = models.PositiveIntegerField(default=0)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shortlinks', null=True, blank=True)
    
    def __str__(self):
        return f"{self.short_code} -> {self.original_url}"
    
    def save(self, *args, **kwargs):
        if not self.short_code or self.short_code == '':
            self.short_code = self.generate_short_code()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_short_code(length=6):
        return get_random_string(length)
    
    class Meta:
        ordering = ['-created_at']
