from django.core.management import BaseCommand, call_command
from django.db import transaction
from main.content import read_data
from main.models import City, Governorate


class Command(BaseCommand):
    help = 'Synchronize the documented city/governorate hierarchy without duplicate rows.'

    @transaction.atomic
    def handle(self, *args, **options):
        call_command('sync_cities', verbosity=0)
        geography = read_data('geography.json')
        content = read_data('governorates.json')
        for region_key, region in geography['regions'].items():
            capital = City.objects.get(slug=region['capital_slug'])
            for order, entry in enumerate(region['governorates'], 1):
                raw = content[f"{region_key}:{entry['slug']}"]
                Governorate.objects.update_or_create(region_key=region_key, slug=entry['slug'], defaults={
                    'name': entry['name'], 'english_name': raw['english_name'],
                    'summary': raw['intro'], 'capital': capital, 'order': order,
                })
        self.stdout.write(self.style.SUCCESS(f'Synchronized {len(geography["capital_slugs"])} capitals and {Governorate.objects.count()} governorates.'))
