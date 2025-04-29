from django import forms
from django.forms import inlineformset_factory
from .models import Post, PostImage, DownloadLink, Manga, MangaDownloadLink, Comment, Contact, MangaComment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'slug', 'categories', 'actresses', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4}),
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
        }

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        }

PostImageFormSet = inlineformset_factory(
    Post,
    PostImage,
    fields=['image', 'is_thumbnail', 'order'],
    extra=1,
    can_delete=True
)

DownloadLinkFormSet = inlineformset_factory(
    Post,
    DownloadLink,
    fields=['host_type', 'url', 'order'],
    extra=1,
    can_delete=True
)

class MangaForm(forms.ModelForm):
    class Meta:
        model = Manga
        fields = ['title', 'slug', 'categories', 'authors', 'tags', 'description', 'pdf_file']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

MangaDownloadLinkFormSet = inlineformset_factory(
    Manga,
    MangaDownloadLink,
    fields=['host_type', 'url'],
    extra=1,
    can_delete=True
)

class MangaCommentForm(forms.ModelForm):
    class Meta:
        model = MangaComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your comment here...'}),
        } 