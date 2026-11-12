from django.urls import path
from django.views.generic import RedirectView
from django.views.i18n import set_language
from . import views

app_name = 'main'
urlpatterns = [
    path('preferences/language/', set_language, name='set_language'),
    path('home/', views.home, name='home'),
    path('', RedirectView.as_view(url='home/', permanent=False)),
    path('culture/<slug:topic>/', views.culture_topic, name='culture_topic'),
    path('cities/', views.city_list, name='cities'),
    path('cities/<slug:capital_slug>/governorates/<slug:slug>/', views.governorate_detail, name='governorate_detail'),
    path('cities/<slug:capital_slug>/governorates/<slug:slug>/save/', views.toggle_governorate_saved, name='toggle_governorate_saved'),
    path('cities/<slug:slug>/', views.city_detail, name='city_detail'),
    path('cities/<slug:slug>/save/', views.toggle_saved, name='toggle_saved'),
    path('about/', views.about, name='about'),
    path('preferences/theme/', views.set_theme, name='set_theme'),
]
