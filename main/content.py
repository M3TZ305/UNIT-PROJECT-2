"""Read JSON once per modification, so data edits refresh automatically."""
import json
import unicodedata
from functools import lru_cache
from django.conf import settings


@lru_cache(maxsize=4)
def _read_json(path, modified):
    with path.open(encoding='utf-8') as source:
        return json.load(source)


def read_data(filename):
    path = settings.BASE_DIR / 'data' / filename
    return _read_json(path, path.stat().st_mtime_ns)


def get_catalog():
    return read_data('cities.json')


def get_media():
    return read_data('media.json')


def search_key(text):
    """Ignore Arabic vocalization and common alef variants when searching."""
    return ''.join(char for char in unicodedata.normalize('NFKD', text)
                   if not unicodedata.combining(char)).casefold().replace('ى', 'ي')
