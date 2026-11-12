import hashlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import translation
from .models import City, Governorate
from .media_delivery import cdn_url
from .templatetags.site_assets import localize


class LanguageReleaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('sync_geography', verbosity=0)

    def test_arabic_default_and_explicit_english_cookie(self):
        self.assertContains(self.client.get('/home/'), 'lang="ar" dir="rtl"')
        response = self.client.post(reverse('main:set_language'), {'language': 'en', 'next': '/cities/'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/cities/')
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, 'en')
        self.assertTrue(response.cookies[settings.LANGUAGE_COOKIE_NAME]['httponly'])
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME]['samesite'], 'Lax')
        home = self.client.get('/home/')
        self.assertContains(home, 'lang="en" dir="ltr"')
        self.assertContains(home, 'Taleed')
        self.assertContains(home, 'Explore cities')
        self.assertNotContains(home, 'Giving birth')
        self.assertEqual(home['Content-Language'], 'en')

    def test_language_switch_requires_csrf_and_rejects_external_redirect(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('main:set_language'), {'language': 'en'}).status_code, 403)
        client.get('/home/')
        token = client.cookies['csrftoken'].value
        response = client.post(reverse('main:set_language'), {'language': 'en', 'next': 'https://example.invalid/'}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response['Location'], '/')
        response = self.client.post(reverse('main:set_language'), {'language': 'xx', 'next': '/home/'})
        self.assertNotIn(settings.LANGUAGE_COOKIE_NAME, response.cookies)

    def test_english_place_names_cuisine_and_theme_work_together(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'en'
        self.client.post(reverse('main:set_theme'), {'theme': 'dark'})
        page = self.client.get('/cities/madinah/governorates/mahd-al-dhahab/')
        self.assertContains(page, 'Mahd adh Dhahab')
        self.assertContains(page, 'Khawadah')
        self.assertContains(page, 'data-theme="dark"')
        self.assertNotContains(page, 'Cradle of gold')
        self.assertContains(page, 'khawadah-v1-cutout.webp')
        self.client.post(reverse('main:set_language'), {'language': 'ar', 'next': '/home/'})
        self.assertContains(self.client.get('/home/'), 'lang="ar" dir="rtl"')

    def test_every_place_renders_in_english(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'en'
        urls = {place.get_absolute_url() for place in City.objects.all()}
        urls.update(place.get_absolute_url() for place in Governorate.objects.select_related('capital'))
        urls.update(['/home/', '/cities/', '/about/', '/culture/architecture/', '/culture/crafts/', '/culture/food/'])
        self.assertEqual(len(urls), 57)
        for url in urls:
            with self.subTest(url=url):
                page = self.client.get(url)
                self.assertEqual(page.status_code, 200)
                self.assertContains(page, 'lang="en" dir="ltr"')
                self.assertContains(page, 'class="th-footer"', count=1)

    def test_sources_catalogue_is_removed_but_inline_credits_remain(self):
        self.assertEqual(self.client.get('/sources/').status_code, 404)
        for url in ['/home/', '/about/', '/cities/', '/cities/madinah/']:
            page = self.client.get(url)
            self.assertNotContains(page, 'href="/sources/"')
        page = self.client.get('/cities/madinah/')
        self.assertContains(page, 'class="photo-credit"')
        for landmark in page.context['atlas']['landmarks']:
            if landmark.get('image'):
                self.assertContains(page, landmark['image']['source'])
                self.assertContains(page, landmark['image']['license_url'])

    def test_new_local_cuisine_is_translated_without_inherited_provenance(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'en'
        page = self.client.get('/cities/dammam/governorates/qatif/')
        self.assertContains(page, 'Qatif mahmoos')
        self.assertContains(page, 'qatif-mahmoos-v1-cutout.webp')
        self.assertEqual(page.context['profile']['culture']['dishes'][0]['evidence_scope'], 'local')
        page = self.client.get('/cities/dammam/governorates/al-ahsa/')
        self.assertContains(page, 'Hasawi rice')
        self.assertEqual(len(page.context['profile']['culture']['dishes']), 2)

    def test_localization_never_changes_urls_or_non_text_values(self):
        with translation.override('en'):
            self.assertEqual(localize('مهد الذهب'), 'Mahd adh Dhahab')
            self.assertEqual(localize('الحجر'), 'Stone')
            self.assertEqual(localize('الحجر', 'landmark'), 'Al-Hijr — Hegra')
            self.assertEqual(localize('/cities/madinah/'), '/cities/madinah/')
            self.assertEqual(localize(4), 4)
            self.assertEqual(localize({'slug': 'madinah'}), {'slug': 'madinah'})


class DeliveryReleaseTests(SimpleTestCase):
    def test_cdn_requires_https_allowed_host_and_matching_local_content(self):
        with tempfile.TemporaryDirectory(dir=settings.BASE_DIR) as folder:
            root = Path(folder)
            (root / 'static/images').mkdir(parents=True)
            image = root / 'static/images/example.jpg'
            image.write_bytes(b'test image')
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            valid = {'images/example.jpg': {'url': 'https://res.cloudinary.com/demo/image/upload/example.jpg', 'sha256': digest}}
            with override_settings(BASE_DIR=root), patch('main.media_delivery.read_data', return_value=valid):
                self.assertEqual(cdn_url('images/example.jpg'), valid['images/example.jpg']['url'])
                valid['images/example.jpg']['sha256'] = 'wrong'
                self.assertIsNone(cdn_url('images/example.jpg'))
                valid['images/example.jpg'].update(sha256=digest, url='https://example.invalid/image.jpg')
                self.assertIsNone(cdn_url('images/example.jpg'))

    def test_export_and_dry_run_never_upload_files(self):
        with tempfile.TemporaryDirectory(dir=settings.BASE_DIR) as folder:
            root = Path(folder)
            (root / 'static/images').mkdir(parents=True)
            (root / 'data').mkdir()
            (root / 'static/images/test.jpg').write_bytes(b'test image')
            (root / 'data/media.json').write_text('{}', encoding='utf-8')
            (root / 'data/design_assets.json').write_text('[]', encoding='utf-8')
            with override_settings(BASE_DIR=root), patch('urllib.request.urlopen') as upload:
                call_command('export_media', stdout=io.StringIO())
                call_command('upload_cdn', stdout=io.StringIO())
                self.assertTrue((root / 'release/media-upload.zip').exists())
                self.assertEqual(len(json.loads((root / 'release/cdn-upload.json').read_text())), 1)
                upload.assert_not_called()


class TransparentCultureAssetTests(SimpleTestCase):
    def test_cultural_cutouts_have_real_transparency(self):
        files = list((settings.BASE_DIR / 'static/images/culture').glob('*-cutout.webp'))
        self.assertEqual(len(files), 12)
        for file in files:
            with self.subTest(file=file.name):
                data = file.read_bytes()
                self.assertEqual(data[:4], b'RIFF')
                self.assertEqual(data[8:12], b'WEBP')
                chunks = {}
                offset = 12
                while offset + 8 <= len(data):
                    size = int.from_bytes(data[offset + 4:offset + 8], 'little')
                    chunks[data[offset:offset + 4]] = data[offset + 8:offset + 8 + size]
                    offset += 8 + size + size % 2
                if b'VP8L' in chunks:
                    self.assertEqual(chunks[b'VP8L'][0], 0x2f)
                    self.assertTrue(int.from_bytes(chunks[b'VP8L'][1:5], 'little') & (1 << 28))
                else:
                    self.assertTrue(chunks[b'VP8X'][0] & 0x10)
                    self.assertGreater(len(chunks[b'ALPH']), 100)

