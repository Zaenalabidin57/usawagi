from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
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
    path('profile/<str:username>/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('api/categories/', views.get_categories, name='get_categories'),
]
