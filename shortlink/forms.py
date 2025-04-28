from django import forms
from .models import ShortLink

class ShortLinkForm(forms.ModelForm):
    class Meta:
        model = ShortLink
        fields = ['original_url', 'title', 'description', 'short_code']
        widgets = {
            'original_url': forms.URLInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'https://example.com'}),
            'title': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'Optional title for your link'}),
            'description': forms.Textarea(attrs={'class': 'textarea textarea-bordered w-full', 'placeholder': 'Optional description', 'rows': 3}),
            'short_code': forms.TextInput(attrs={'class': 'input input-bordered w-full', 'placeholder': 'Leave blank for auto-generated code', 'required': False}),
        }
        labels = {
            'original_url': 'Original URL',
            'title': 'Title (Optional)',
            'description': 'Description (Optional)',
            'short_code': 'Custom Short Code (Optional)',
        }
        help_texts = {
            'short_code': 'Leave blank to generate automatically, or enter your own custom code',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make short_code not required in the form
        self.fields['short_code'].required = False
    
    def clean_short_code(self):
        short_code = self.cleaned_data.get('short_code')
        if not short_code or short_code.strip() == '':  # If empty or just whitespace, return None to trigger auto-generation
            return ''
        
        # If this is an update and the short_code hasn't changed, allow it
        if self.instance.pk and self.instance.short_code == short_code:
            return short_code
        
        # Check if the short_code already exists
        if ShortLink.objects.filter(short_code=short_code).exists():
            raise forms.ValidationError('This short code is already in use. Please choose another one.')
        
        return short_code
