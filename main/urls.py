from django.urls import path
from . import views

app_name = 'main'
urlpatterns = [
    path('', views.home, name='home'),
    path('cities/', views.city_list, name='cities'),
    path('cities/<slug:slug>/', views.city_detail, name='city_detail'),
    path('cities/<slug:slug>/save/', views.toggle_saved, name='toggle_saved'),
    path('about/', views.about, name='about'),
    path('sources/', views.sources, name='sources'),
    path('preferences/theme/', views.set_theme, name='set_theme'),
]
