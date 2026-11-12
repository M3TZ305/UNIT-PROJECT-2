"""Prepare responsive local photographs offline; originals remain available for zoom."""
import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from main.content import read_data


class Command(BaseCommand):
    help = 'Generate 640px/1280px WebP photographs and refresh their manifest.'

    def handle(self, *args, **options):
        try:
            from PIL import Image
        except ImportError as exc:
            raise CommandError('Install Pillow to rebuild image variants. Serving the site does not require it.') from exc
        root = (settings.BASE_DIR / 'static').resolve()
        variants = {}
        for entry in read_data('media.json').values():
            relative = entry['fallback']
            source = (root / relative).resolve()
            if not entry.get('prefer_local') or relative in variants:
                continue
            if not source.is_relative_to(root) or not source.is_file():
                raise CommandError(f'Invalid local photograph: {relative}')
            if source.suffix.lower() not in ('.jpg', '.jpeg', '.webp', '.png'):
                continue
            with Image.open(source) as image:
                if image.width <= 900 or 'A' in image.getbands():
                    continue
                entries = []
                for width in (640, 1280):
                    if image.width <= width:
                        continue
                    target = source.with_name(f'{source.stem}-w{width}.webp')
                    if not target.exists() or target.stat().st_mtime_ns < source.stat().st_mtime_ns:
                        resized = image.copy()
                        resized.thumbnail((width, 10000))
                        resized.save(target, 'WEBP', quality=84, method=4)
                    entries.append({'file': target.relative_to(root).as_posix(), 'width': width})
                if entries:
                    variants[relative] = entries
        manifest = settings.BASE_DIR / 'data/responsive_images.json'
        manifest.write_text(json.dumps(variants, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        self.stdout.write(f'Prepared {len(variants)} responsive photograph sets. No images uploaded.')
