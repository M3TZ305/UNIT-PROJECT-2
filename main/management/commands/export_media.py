"""Build a local CDN upload package without transmitting anything."""
import json
import zipfile
from hashlib import sha256
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from main.content import read_data


class Command(BaseCommand):
    help = 'Prepare release/media-upload.zip and a checksum manifest; does not upload.'

    def handle(self, *args, **options):
        root = settings.BASE_DIR / 'static'
        destination = settings.BASE_DIR / 'release'
        destination.mkdir(exist_ok=True)
        entries = []
        with zipfile.ZipFile(destination / 'media-upload.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted((root / 'images').rglob('*')):
                if not path.is_file():
                    continue
                relative = path.relative_to(root).as_posix()
                entries.append({'path': relative, 'bytes': path.stat().st_size,
                                'sha256': sha256(path.read_bytes()).hexdigest()})
                archive.write(path, relative)
            archive.writestr('credits.json', json.dumps(read_data('media.json'), ensure_ascii=False, indent=2))
            archive.writestr('illustrations.json', json.dumps(read_data('design_assets.json'), ensure_ascii=False, indent=2))
        (destination / 'cdn-upload.json').write_text(json.dumps(entries, indent=2), encoding='utf-8')
        self.stdout.write(f'Prepared {len(entries)} files locally. No files were uploaded.')
