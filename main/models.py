from django.db import models
from django.utils.functional import cached_property
from .content import get_catalog, get_media


class City(models.Model):
    """Searchable database index; detailed editorial content lives in JSON."""
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    english_name = models.CharField(max_length=80)
    region = models.CharField(max_length=80)
    region_key = models.SlugField()
    summary = models.TextField()
    topics = models.JSONField(default=list)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'مدينة'
        verbose_name_plural = 'المدن'

    def __str__(self):
        return self.name

    @cached_property
    def data(self):
        data = get_catalog()['cities'][self.slug].copy()
        media = get_media()
        data['hero'] = media[data['hero_key']]
        data['gallery'] = [{**media[item['key']], 'caption': item['caption']}
                           for item in data['gallery']]
        return data

    @property
    def number(self):
        return f'{self.order:02d}'
