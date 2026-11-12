"""Explicit signed Cloudinary upload; credentials never enter project files."""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from main.media_delivery import file_digest


def multipart(fields, path):
    boundary = 'Taleed' + uuid.uuid4().hex
    chunks = []
    for key, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode())
    chunks += [path.read_bytes(), f'\r\n--{boundary}--\r\n'.encode()]
    return b''.join(chunks), boundary


class Command(BaseCommand):
    help = 'Dry-run by default. Use --upload only after configuring your Cloudinary account.'

    def add_arguments(self, parser):
        parser.add_argument('--upload', action='store_true')
        parser.add_argument('--limit', type=int, default=0)

    def handle(self, *args, **options):
        manifest_path = settings.BASE_DIR / 'release' / 'cdn-upload.json'
        if not manifest_path.exists():
            raise CommandError('Run manage.py export_media first.')
        entries = json.loads(manifest_path.read_text(encoding='utf-8'))
        if options['limit'] > 0:
            entries = entries[:options['limit']]
        if not options['upload']:
            self.stdout.write(f'Dry run: {len(entries)} files are ready. No credentials read and no network requests made.')
            return
        names = ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']
        if any(not os.environ.get(name) for name in names):
            raise CommandError('Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET privately in your environment.')
        cloud, api_key, secret = (os.environ[name] for name in names)
        if not all(c.isalnum() or c in '-_' for c in cloud):
            raise CommandError('Invalid cloud name.')
        root = (settings.BASE_DIR / 'static').resolve()
        mapping_path = settings.BASE_DIR / 'data' / 'cdn_manifest.json'
        mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
        for entry in entries:
            path = (root / entry['path']).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise CommandError('Upload manifest contains an invalid local path.')
            digest = file_digest(path, path.stat().st_mtime_ns)
            if digest != entry['sha256']:
                raise CommandError('An image changed. Run export_media again before uploading.')
            if mapping.get(entry['path'], {}).get('sha256') == digest:
                continue
            fields = {'public_id': 'taleed/' + digest, 'timestamp': str(int(time.time())), 'overwrite': 'false'}
            signature = hashlib.sha1(('&'.join(f'{key}={fields[key]}' for key in sorted(fields)) + secret).encode()).hexdigest()
            fields.update(api_key=api_key, signature=signature)
            body, boundary = multipart(fields, path)
            request = urllib.request.Request(f'https://api.cloudinary.com/v1_1/{cloud}/image/upload', data=body,
                                             headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
            try:
                with urllib.request.urlopen(request, timeout=90) as response:
                    result = json.load(response)
            except (urllib.error.URLError, ValueError):
                raise CommandError('Cloud upload failed. Previously recorded uploads are preserved; credentials were not logged.') from None
            url = result.get('secure_url', '')
            if not url.startswith('https://res.cloudinary.com/'):
                raise CommandError('Upload did not return a valid secure delivery URL.')
            if path.suffix.lower() != '.svg':
                url = url.replace('/image/upload/', '/image/upload/f_auto,q_auto/', 1)
            mapping[entry['path']] = {'url': url, 'sha256': digest}
            temporary = mapping_path.with_suffix('.tmp')
            temporary.write_text(json.dumps(mapping, indent=2) + '\n', encoding='utf-8')
            temporary.replace(mapping_path)
            self.stdout.write('Uploaded ' + entry['path'])
        self.stdout.write('CDN manifest saved. Original credits and local fallbacks remain available.')
