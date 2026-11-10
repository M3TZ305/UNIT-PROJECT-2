from django.contrib import admin
from .models import City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['order', 'name', 'english_name', 'region']
    search_fields = ['name', 'english_name', 'region']

from .models import Governorate
admin.site.register(Governorate)
