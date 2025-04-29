from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='index'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.post_detail, name='post_detail'),
    path('create-post/', views.create_post, name='create_post'),
    path('edit-post/<slug:slug>/', views.edit_post, name='edit_post'),
    path('delete-post/<slug:slug>/', views.delete_post, name='delete_post'),
    path('like-post/<slug:slug>/', views.like_post, name='like_post'),
    path('delete-image/<int:image_id>/', views.delete_image, name='delete_image'),
    path('comment/<slug:slug>/', views.add_comment, name='add_comment'),
    path('comment/delete/<int:comment_id>/', views.delete_comment, name='delete_comment'),
    path('contact/', views.contact, name='contact'),
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.signout, name='logout'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('api/categories/', views.get_categories, name='get_categories'),
    
    # Random post
    path('random/', views.random_post, name='random_post'),
    
    # Manga URLs
    path('manga/', views.manga_list, name='manga_list'),
    path('manga/create/', views.create_manga, name='create_manga'),
    path('manga/view/<slug:slug>/', views.manga_view, name='manga_view'),
    path('manga/download/<slug:slug>/', views.manga_download, name='manga_download'),
    path('manga/edit/<slug:slug>/', views.edit_manga, name='edit_manga'),
    path('manga/delete/<slug:slug>/', views.delete_manga, name='delete_manga'),
    path('manga/like/<slug:slug>/', views.like_manga, name='like_manga'),
    path('manga/<slug:slug>/', views.manga_detail, name='manga_detail'),
    
    # Bookmark URLs
    path('bookmark/', views.bookmark_item, name='bookmark_item'),
    path('bookmark/remove/<int:bookmark_id>/', views.remove_bookmark, name='remove_bookmark'),
    path('user/<str:username>/bookmarks/', views.user_bookmarks, name='user_bookmarks'),
]
