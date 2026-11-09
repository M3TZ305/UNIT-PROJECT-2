from django.core.management.base import BaseCommand
from django.db import transaction
from main.content import get_catalog
from main.models import City


class Command(BaseCommand):
    help = 'Update the searchable city index from data/cities.json; safe to repeat.'

    @transaction.atomic
    def handle(self, *args, **options):
        for order, (slug, data) in enumerate(get_catalog()['cities'].items(), start=1):
            City.objects.update_or_create(slug=slug, defaults={
                'name': data['name'], 'english_name': data['english_name'],
                'region': data['region'], 'region_key': data['region_key'],
                'summary': data['summary'], 'topics': data['topics'], 'order': order,
            })
        self.stdout.write(self.style.SUCCESS('City index synchronized from JSON.'))
