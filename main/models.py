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
        from .content import read_data
        doorway = read_data('city_doors.json').get(self.slug, {})
        data['hero'] = media[doorway.get('image_key', data['hero_key'])]
        data['gallery'] = [{**media[item['key']], 'caption': item['caption']}
                           for item in data['gallery']]
        return data

    @cached_property
    def atlas(self):
        from .atlas import city_atlas
        return city_atlas(self.slug)

    @property
    def number(self):
        from .geography import capital_slugs
        slugs = capital_slugs()
        number = slugs.index(self.slug) + 1 if self.slug in slugs else self.order
        return f'{number:02d}'


    @property
    def saved_key(self):
        from .geography import registry
        return registry().get('legacy_city_keys', {}).get(self.slug, self.slug)

    def get_absolute_url(self):
        from django.urls import reverse
        from .geography import registry
        key = registry().get('legacy_city_keys', {}).get(self.slug)
        if key:
            _, region, slug = key.split(':')
            return reverse('main:governorate_detail', kwargs={'capital_slug': registry()['regions'][region]['capital_slug'], 'slug': slug})
        return reverse('main:city_detail', kwargs={'slug': self.slug})

    def get_save_url(self):
        from django.urls import reverse
        return reverse('main:toggle_saved', kwargs={'slug': self.slug})


class Governorate(models.Model):
    """Searchable governorate index; source-backed editorial details live in JSON."""
    slug = models.SlugField()
    region_key = models.SlugField()
    name = models.CharField(max_length=100)
    english_name = models.CharField(max_length=120, blank=True)
    summary = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)
    capital = models.ForeignKey(City, on_delete=models.PROTECT, related_name='governorates')

    class Meta:
        ordering = ['order', 'name']
        constraints = [models.UniqueConstraint(fields=['region_key', 'slug'], name='unique_governorate_region_slug')]
        verbose_name = 'محافظة'
        verbose_name_plural = 'المحافظات'

    def __str__(self):
        return self.name

    @property
    def region(self):
        return self.capital.region

    @property
    def saved_key(self):
        return f'gov:{self.region_key}:{self.slug}'

    @property
    def number(self):
        return f'{self.order:02d}'

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('main:governorate_detail', kwargs={'capital_slug': self.capital.slug, 'slug': self.slug})

    def get_save_url(self):
        from django.urls import reverse
        return reverse('main:toggle_governorate_saved', kwargs={'capital_slug': self.capital.slug, 'slug': self.slug})

    @cached_property
    def data(self):
        from .geography import governorate_data
        return governorate_data(self)

    @cached_property
    def atlas(self):
        from .geography import governorate_atlas
        return governorate_atlas(self)
