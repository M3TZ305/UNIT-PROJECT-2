"""Optional verified CDN URLs, with unchanged local image fallbacks."""
from functools import lru_cache
from hashlib import sha256
from urllib.parse import urlsplit
from django.conf import settings
from .content import read_data


@lru_cache(maxsize=512)
def file_digest(path, modified):
    return sha256(path.read_bytes()).hexdigest()


def cdn_url(relative_path, mapping=None):
    if mapping is None:
        mapping = read_data('cdn_manifest.json')
    entry = mapping.get(relative_path)
    if not isinstance(entry, dict):
        return None
    url = entry.get('url', '')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'res.cloudinary.com':
        return None
    root = (settings.BASE_DIR / 'static').resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return None
    if entry.get('sha256') != file_digest(path, path.stat().st_mtime_ns):
        return None
    return url
