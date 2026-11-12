"""Read JSON once per modification, so data edits refresh automatically."""
import json
import unicodedata
from functools import lru_cache
from django.conf import settings


@lru_cache(maxsize=32)
def _read_json(path, modified):
    with path.open(encoding='utf-8') as source:
        return json.load(source)


def read_data(filename):
    path = settings.BASE_DIR / 'data' / filename
    return _read_json(path, path.stat().st_mtime_ns)


def get_catalog():
    return read_data('cities.json')


def get_media():
    from .media_delivery import cdn_url
    from django.templatetags.static import static
    mapping = read_data('cdn_manifest.json')
    variants = read_data('responsive_images.json')
    return {key: {**value, 'srcset': ', '.join(static(item['file']) + ' ' + str(item['width']) + 'w' for item in variants.get(value['fallback'], [])) if value.get('prefer_local') else '', 'url': cdn_url(value['fallback'], mapping) or (static(value['fallback']) if value.get('prefer_local') else value['url'])}
            for key, value in read_data('media.json').items()}


def search_key(text):
    """Ignore Arabic vocalization and common alef variants when searching."""
    return ''.join(char for char in unicodedata.normalize('NFKD', text)
                   if not unicodedata.combining(char)).casefold().replace('ى', 'ي')
