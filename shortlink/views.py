from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import Http404
from .models import ShortLink
from .forms import ShortLinkForm

def redirect_to_original(request, short_code):
    shortlink = get_object_or_404(ShortLink, short_code=short_code)
    
    # Increment the click counter
    shortlink.clicks += 1
    shortlink.save()
    
    context = {
        'shortlink': shortlink,
    }
    return render(request, 'shortlink/redirect_page.html', context)

@login_required(login_url='signin')
def create_shortlink(request):
    if request.method == 'POST':
        form = ShortLinkForm(request.POST)
        if form.is_valid():
            shortlink = form.save(commit=False)
            shortlink.creator = request.user
            shortlink.save()
            messages.success(request, f"Short link created successfully: {shortlink.short_code}")
            return redirect('shortlink_dashboard')
    else:
        form = ShortLinkForm()
    
    context = {
        'form': form,
    }
    return render(request, 'shortlink/create.html', context)

@login_required(login_url='signin')
def shortlink_dashboard(request):
    user_shortlinks = ShortLink.objects.filter(creator=request.user)
    
    context = {
        'shortlinks': user_shortlinks,
    }
    return render(request, 'shortlink/dashboard.html', context)

@login_required(login_url='signin')
def edit_shortlink(request, short_code):
    shortlink = get_object_or_404(ShortLink, short_code=short_code, creator=request.user)
    
    if request.method == 'POST':
        form = ShortLinkForm(request.POST, instance=shortlink)
        if form.is_valid():
            form.save()
            messages.success(request, f"Short link updated successfully: {shortlink.short_code}")
            return redirect('shortlink_dashboard')
    else:
        form = ShortLinkForm(instance=shortlink)
    
    context = {
        'form': form,
        'shortlink': shortlink,
    }
    return render(request, 'shortlink/edit.html', context)

@login_required(login_url='signin')
def delete_shortlink(request, short_code):
    shortlink = get_object_or_404(ShortLink, short_code=short_code, creator=request.user)
    
    if request.method == 'POST':
        shortlink.delete()
        messages.success(request, "Short link deleted successfully")
        return redirect('shortlink_dashboard')
    
    context = {
        'shortlink': shortlink,
    }
    return render(request, 'shortlink/delete.html', context)
