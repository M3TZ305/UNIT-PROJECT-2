import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import resolve, reverse

from .content import get_catalog, get_media
from .models import City


class MalamihTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('sync_cities', verbosity=0)

    def test_all_pages_use_shared_template(self):
        paths = ['/', '/cities/', '/about/', '/sources/']
        paths += [reverse('main:city_detail', kwargs={'slug': city.slug}) for city in City.objects.all()]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'base.html')
                self.assertNotContains(response, 'src=""')

    def test_path_parameter_and_named_url(self):
        url = reverse('main:city_detail', kwargs={'slug': 'jeddah'})
        self.assertEqual(resolve(url).kwargs, {'slug': 'jeddah'})
        self.assertTemplateUsed(self.client.get(url), 'main/city_detail.html')

    def test_home_stays_editorial_without_city_grid(self):
        response = self.client.get('/')
        self.assertNotContains(response, 'cities-grid')
        self.assertContains(response, '?category=crafts')

    def test_arabic_and_english_search(self):
        for query, slug in [('جدة', 'jeddah'), ('العلا', 'alula'), ('RIYADH', 'riyadh'), ('أبها', 'abha')]:
            with self.subTest(query=query):
                response = self.client.get('/cities/', {'q': query})
                self.assertEqual([city.slug for city in response.context['cities']], [slug])

    def test_filters_combine(self):
        response = self.client.get('/cities/', {'region': 'east', 'category': 'crafts'})
        self.assertEqual([city.slug for city in response.context['cities']], ['hofuf'])

    def test_empty_search_has_recovery_link(self):
        response = self.client.get('/cities/', {'q': 'not-a-real-city'})
        self.assertEqual(response.context['result_count'], 0)
        self.assertContains(response, 'اكتشف كل المدن')

    def test_invalid_filters_and_long_query(self):
        response = self.client.get('/cities/', {'category': 'bad', 'region': 'bad', 'q': 'a'*1000})
        self.assertEqual(response.context['category'], '')
        self.assertEqual(response.context['region'], '')
        self.assertEqual(len(response.context['query']), 100)

    def test_search_is_escaped(self):
        response = self.client.get('/cities/', {'q': '<script>alert(1)</script>'})
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_theme_cookie_persists(self):
        response = self.client.post('/preferences/theme/', {'theme': 'dark', 'next': '/cities/'})
        self.assertRedirects(response, '/cities/')
        self.assertTrue(response.cookies['theme']['httponly'])
        self.assertContains(self.client.get('/'), 'data-theme="dark"')

    def test_invalid_theme_falls_back(self):
        self.client.cookies['theme'] = 'invalid'
        self.assertContains(self.client.get('/'), 'data-theme="light"')
        response = self.client.post('/preferences/theme/', {'theme': 'invalid'})
        self.assertEqual(response.cookies['theme'].value, 'light')

    def test_preference_redirect_rejects_external_url(self):
        for target in ['https://evil.example/', '//evil.example/']:
            response = self.client.post('/preferences/theme/', {'theme': 'dark', 'next': target})
            self.assertEqual(response['Location'], '/')

    def test_ajax_theme_response(self):
        response = self.client.post('/preferences/theme/', {'theme': 'dark'}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.json(), {'theme': 'dark'})

    def test_save_remove_and_saved_filter(self):
        url = reverse('main:toggle_saved', kwargs={'slug': 'jeddah'})
        response = self.client.post(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.json()['count'], 1)
        response = self.client.get('/cities/', {'saved': 1})
        self.assertEqual([city.slug for city in response.context['cities']], ['jeddah'])
        response = self.client.post(url, HTTP_ACCEPT='application/json')
        self.assertFalse(response.json()['saved'])
        self.assertEqual(self.client.get('/cities/', {'saved': 1}).context['result_count'], 0)

    def test_malformed_saved_cookies(self):
        for cookie in ['bad-json', '{}', 'null', '[1, {}, "bad", "jeddah", "jeddah"]']:
            self.client.cookies['saved_cities'] = cookie
            response = self.client.get('/cities/', {'saved': 1})
            self.assertEqual(response.status_code, 200)
            self.assertLessEqual(response.context['result_count'], 1)

    def test_mutations_require_post_and_csrf(self):
        secure_client = Client(enforce_csrf_checks=True)
        for url in ['/preferences/theme/', '/cities/jeddah/save/']:
            self.assertEqual(secure_client.get(url).status_code, 405)
            self.assertEqual(secure_client.post(url, {'theme': 'dark'}).status_code, 403)
        secure_client.get('/')
        csrf = secure_client.cookies['csrftoken'].value
        response = secure_client.post('/preferences/theme/', {'theme': 'dark', 'csrfmiddlewaretoken': csrf})
        self.assertEqual(response.status_code, 302)

    @override_settings(DEBUG=False)
    def test_missing_city_has_custom_404(self):
        response = self.client.get('/cities/missing/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_city_content_and_media_are_complete(self):
        catalog, media = get_catalog(), get_media()
        self.assertEqual(City.objects.count(), 6)
        self.assertEqual(len(catalog['cities']), 6)
        for city in City.objects.all():
            self.assertEqual(len(city.data['sections']), 3)
            self.assertGreaterEqual(len(city.data['gallery']), 3)
            self.assertTrue(re.fullmatch(r'[A-Za-z0-9_-]{11}', city.data['video']['id']))
            self.assertTrue(city.data['sources'])
            self.assertTrue(city.data['timeline'])
        for item in media.values():
            self.assertTrue(item['url'].startswith('https://'))
            self.assertTrue(item['author'])
            self.assertTrue(item['license'])
            self.assertTrue((settings.BASE_DIR / 'static' / item['fallback']).is_file())

    def test_sync_is_idempotent(self):
        original = list(City.objects.values_list('slug', 'pk'))
        call_command('sync_cities', verbosity=0)
        self.assertEqual(list(City.objects.values_list('slug', 'pk')), original)
