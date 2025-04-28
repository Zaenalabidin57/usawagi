from django.urls import path
from . import views

urlpatterns = [
    path('', views.shortlink_dashboard, name='shortlink_dashboard'),
    path('create/', views.create_shortlink, name='create_shortlink'),
    path('dashboard/', views.shortlink_dashboard, name='shortlink_dashboard_alt'),
    path('edit/<str:short_code>/', views.edit_shortlink, name='edit_shortlink'),
    path('delete/<str:short_code>/', views.delete_shortlink, name='delete_shortlink'),
    path('<str:short_code>/', views.redirect_to_original, name='redirect_to_original'),
]
