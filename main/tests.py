import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import resolve, reverse

from .content import get_catalog, get_media
from .models import City, Governorate
from .geography import capital_slugs, registry


class TaleedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('sync_geography', verbosity=0)

    def test_all_pages_use_shared_template(self):
        paths = ['/', '/cities/', '/about/', '/sources/', '/culture/architecture/', '/culture/crafts/', '/culture/food/']
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
        self.assertContains(response, reverse('main:culture_topic', kwargs={'topic': 'crafts'}))

    def test_arabic_and_english_search(self):
        for query, slug in [('جدة', 'makkah'), ('العلا', 'madinah'), ('RIYADH', 'riyadh'), ('أبها', 'abha')]:
            with self.subTest(query=query):
                response = self.client.get('/cities/', {'q': query})
                self.assertEqual([city.slug for city in response.context['cities']], [slug])

    def test_filters_combine(self):
        response = self.client.get('/cities/', {'region': 'east', 'category': 'crafts'})
        cities = response.context['cities']
        self.assertEqual([city.slug for city in cities], ['dammam'])
        self.assertTrue(all(city.region_key == 'east' and 'crafts' in city.topics for city in cities))

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
        self.assertEqual(City.objects.count(), len(catalog['cities']))
        self.assertGreaterEqual(City.objects.count(), 26)
        for city in City.objects.all():
            self.assertEqual(len(city.data['sections']), 3)
            self.assertGreaterEqual(len(city.data['gallery']), 1)
            if city.data['video']:
                self.assertTrue(re.fullmatch(r'[A-Za-z0-9_-]{11}', city.data['video']['id']))
            self.assertTrue((settings.BASE_DIR / 'static' / city.data['chapter_art']['file']).is_file())
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

    def test_chapters_start_with_madinah_and_cover_thirteen_regions(self):
        response = self.client.get('/cities/')
        cities = response.context['cities']
        self.assertEqual(cities[0].slug, 'madinah')
        self.assertEqual(len({city.region for city in cities}), 13)
        self.assertContains(response, 'id="chapter-madinah"')
        self.assertEqual(len(cities), 13)
        self.assertEqual([city.slug for city in cities], capital_slugs())

    def test_administrative_province_filter(self):
        response = self.client.get('/cities/', {'province': 'madinah'})
        self.assertEqual([city.slug for city in response.context['cities']], ['madinah'])
        response = self.client.get('/cities/', {'province': 'not-real'})
        self.assertEqual(response.context['province'], '')

    def test_more_than_six_saved_cities(self):
        slugs = list(City.objects.values_list('slug', flat=True))[:9]
        for slug in slugs:
            response = self.client.post(reverse('main:toggle_saved', kwargs={'slug': slug}), HTTP_ACCEPT='application/json')
            self.assertTrue(response.json()['saved'])
        response = self.client.get('/cities/', {'saved': 1})
        self.assertEqual(response.context['result_count'], 9)

    def test_missing_film_does_not_render_empty_player_link(self):
        response = self.client.get('/cities/madinah/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="film-section"')
        self.assertNotContains(response, 'https://www.youtube.com/watch?v="')

    def test_discovery_opens_a_separate_atlas_for_each_city(self):
        discovery = self.client.get('/cities/')
        for city in City.objects.filter(slug__in=capital_slugs()):
            with self.subTest(city=city.slug):
                url = reverse('main:city_detail', kwargs={'slug': city.slug})
                self.assertContains(discovery, f'href="{url}"')
                response = self.client.get(url)
                self.assertEqual(response.context['city'].slug, city.slug)
                self.assertContains(response, f'data-atlas="{city.slug}"', count=1)
                self.assertNotContains(response, 'data-city-chapter=')
                self.assertEqual(response.content.count(b'<h1 '), 1)

    def test_atlas_content_is_specific_and_complete(self):
        history_texts = set()
        for city in City.objects.all():
            atlas = city.atlas
            self.assertLessEqual(len(atlas['landmarks']), 5)
            self.assertEqual(len(atlas['history']), 3)
            self.assertEqual({p['key'] for p in atlas['people']}, {'food', 'crafts', 'life'})
            self.assertTrue(atlas['sources'])
            for item in atlas['landmarks'] + atlas['history'] + atlas['people']:
                self.assertTrue(item['text'])
                self.assertTrue(item['source']['url'].startswith('https://'))
            history_texts.add(tuple(m['text'] for m in atlas['history']))
        self.assertEqual(len(history_texts), City.objects.count())

    def test_atlas_gallery_keeps_attribution_in_display_order(self):
        from html.parser import HTMLParser
        class GalleryParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.indexes = []
            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                if tag == 'button' and 'data-gallery-index' in values:
                    self.indexes.append(int(values['data-gallery-index']))
        for city in City.objects.all():
            response = self.client.get(reverse('main:city_detail', kwargs={'slug': city.slug}))
            parser = GalleryParser()
            parser.feed(response.content.decode())
            credits = response.context['atlas']['gallery_credits']
            self.assertEqual(parser.indexes, list(range(len(credits))))
            for credit in credits:
                self.assertTrue(credit['author'])
                self.assertTrue(credit['license'])
                self.assertTrue(credit['source'].startswith('https://commons.wikimedia.org/'))

    def test_atlas_images_exist_and_keep_documentary_context(self):
        for city in City.objects.all():
            for landmark in city.atlas['landmarks']:
                if landmark.get('image'):
                    self.assertTrue((settings.BASE_DIR / 'static' / landmark['image']['fallback']).is_file())
                self.assertEqual(landmark['kind'], 'heritage-history')
                self.assertTrue(landmark['scope'])
                self.assertTrue(landmark['caption'])
                self.assertIn('maps/search/?api=1&query=', landmark['map_url'])

    def test_home_cultural_options_open_subject_pages(self):
        response = self.client.get('/')
        for topic in ('architecture', 'crafts', 'food'):
            self.assertContains(response, reverse('main:culture_topic', kwargs={'topic': topic}))
            self.assertNotContains(response, f'?category={topic}')

    def test_culture_routes_present_the_subject_before_the_cities(self):
        expected = {'architecture': 6, 'crafts': 5, 'food': 8}
        for key, count in expected.items():
            response = self.client.get(reverse('main:culture_topic', kwargs={'topic': key}))
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'main/culture_topic.html')
            self.assertEqual(response.context['topic']['key'], key)
            self.assertEqual(len(response.context['topic']['items']), count)
            self.assertContains(response, f'data-culture-topic="{key}"', count=1)
            self.assertNotContains(response, 'data-city-chapter=')
            self.assertContains(response, 'تابع الحكاية في')

    @override_settings(DEBUG=False)
    def test_unknown_cultural_subject_has_a_real_404(self):
        response = self.client.get('/culture/not-a-topic/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')

    def test_cultural_content_has_sources_media_and_valid_city_links(self):
        from .content import read_data
        topics, media = read_data('culture.json'), get_media()
        slugs = set(City.objects.values_list('slug', flat=True))
        for topic in topics.values():
            keys = [item['key'] for item in topic['items']]
            self.assertEqual(len(keys), len(set(keys)))
            for item in topic['items']:
                self.assertTrue(item['source']['url'].startswith('https://'))
                self.assertTrue(item['materials'])
                self.assertTrue(item['steps'])
                self.assertTrue(item['cities'])
                self.assertTrue(set(item['cities']).issubset(slugs))
                if item['photo_key']:
                    self.assertIn(item['photo_key'], media)
                else:
                    self.assertTrue((settings.BASE_DIR / 'static' / item['art']['file']).is_file())

    def test_culture_gallery_orders_photographs_and_preserves_credits(self):
        for key in ('architecture', 'crafts', 'food'):
            response = self.client.get(f'/culture/{key}/')
            photos = [item for item in response.context['topic']['items'] if item.get('photo')]
            indexes = re.findall(r'data-gallery-index="(\d+)"', response.content.decode())
            self.assertEqual([int(index) for index in indexes], list(range(len(photos))))
            for item in photos:
                self.assertContains(response, item['photo']['source'])
                self.assertTrue(item['photo']['license'])

    def test_style_url_revision_changes_after_an_asset_update(self):
        import os
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from .templatetags.site_assets import asset
        with TemporaryDirectory(dir=settings.BASE_DIR) as directory:
            self.assertEqual(Path(directory).resolve().parent, settings.BASE_DIR.resolve())
            css = Path(directory) / 'sample.css'
            css.write_text('body { color: black; }', encoding='utf-8')
            with patch('main.templatetags.site_assets.finders.find', return_value=str(css)):
                first = asset('css/sample.css')
                changed = css.stat().st_mtime_ns + 1_000_000_000
                os.utime(css, ns=(changed, changed))
                second = asset('css/sample.css')
            self.assertNotEqual(first, second)
            self.assertTrue(first.startswith('/static/css/sample.css?v='))


    def test_selected_governorates_have_strict_parent_routes_and_separate_atlases(self):
        self.assertEqual(Governorate.objects.count(), registry()['governorate_count'])
        self.assertEqual(Governorate.objects.count(), 35)
        for slug in capital_slugs():
            capital = City.objects.get(slug=slug)
            self.assertIn(capital.governorates.count(), (2, 3))
            response = self.client.get(capital.get_absolute_url())
            self.assertEqual(len(response.context['governorate_cards']), capital.governorates.count())
            for place in capital.governorates.all():
                with self.subTest(place=place.name):
                    self.assertIn(place.get_absolute_url(), response.content.decode())
                    page = self.client.get(place.get_absolute_url())
                    self.assertEqual(page.status_code, 200)
                    self.assertTemplateUsed(page, 'base.html')
                    self.assertTrue(page.context['is_governorate'])
                    self.assertEqual(page.context['parent_city'], capital)
                    self.assertEqual(page.content.count(b'<h1 '), 1)
                    self.assertNotIn('src=""', page.content.decode())
                    self.assertTrue(place.atlas['history'])
                    self.assertLessEqual(len(place.atlas['landmarks']), 5)
                    self.assertEqual({p['key'] for p in place.atlas['people']}, {'food', 'crafts', 'life'})
                    self.assertTrue(place.data['sources'])
                    self.assertEqual(page.context['governorate_cards'], [])
        self.assertEqual(self.client.get('/cities/riyadh/governorates/alula/').status_code, 404)

    def test_governorate_saving_requires_csrf_and_preserves_legacy_favorites(self):
        place = Governorate.objects.get(slug='alula')
        self.client.cookies['saved_cities'] = json.dumps(['alula', place.saved_key, 'not-real'])
        page = self.client.get('/cities/', {'saved': 1})
        self.assertEqual(page.context['result_count'], 1)
        self.assertEqual(page.context['city_cards'][0]['url'], place.get_absolute_url())
        response = self.client.post(place.get_save_url(), HTTP_ACCEPT='application/json')
        self.assertFalse(response.json()['saved'])
        self.assertEqual(response.json()['slug'], place.saved_key)
        self.assertEqual(response.json()['count'], 0)
        secure = Client(enforce_csrf_checks=True)
        self.assertEqual(secure.get(place.get_save_url()).status_code, 405)
        self.assertEqual(secure.post(place.get_save_url()).status_code, 403)

    def test_governorate_gallery_attribution_and_local_assets(self):
        from html.parser import HTMLParser
        class GalleryParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.indexes = []
            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                if tag == 'button' and 'data-gallery-index' in values:
                    self.indexes.append(int(values['data-gallery-index']))
        for place in Governorate.objects.all():
            page = self.client.get(place.get_absolute_url())
            parser = GalleryParser()
            parser.feed(page.content.decode())
            self.assertEqual(parser.indexes, list(range(len(place.atlas['gallery_credits']))))
            self.assertTrue((settings.BASE_DIR / 'static' / place.data['chapter_art']['file']).is_file())
            for credit in place.atlas['gallery_credits']:
                self.assertTrue(credit['author'])
                self.assertTrue(credit['license'])


    def test_place_profiles_have_dress_two_dishes_and_strict_historical_selection(self):
        from .place_profiles import profile_for, canonical_key
        from .content import read_data
        records = read_data('place_profiles.json')
        self.assertEqual(len(records), 51)
        places = list(City.objects.all()) + list(Governorate.objects.select_related('capital'))
        for place in places:
            key = place.saved_key if isinstance(place, Governorate) else 'city:' + place.slug
            profile = profile_for(key)
            with self.subTest(place=place.name):
                self.assertTrue(profile['fame']['text'])
                self.assertTrue(profile['fame']['source']['url'].startswith('https://'))
                self.assertTrue(profile['culture']['dress']['men']['title'])
                self.assertTrue(profile['culture']['dress']['women']['title'])
                self.assertTrue(profile['culture']['dress']['scope'])
                self.assertEqual(len(profile['culture']['dishes']), 2)
                self.assertEqual(len({d['name'] for d in profile['culture']['dishes']}), 2)
                self.assertLessEqual(len(profile['landmarks']), 5)
                self.assertEqual(len({l['name'] for l in profile['landmarks']}), len(profile['landmarks']))
                for item in profile['landmarks']:
                    self.assertEqual(item['kind'], 'heritage-history')
                    self.assertTrue(item['scope'])
                    self.assertTrue(item['source']['url'].startswith('https://'))
                response = self.client.get(place.get_absolute_url())
                html = response.content.decode()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(html.count('data-dress="men"'), 1)
                self.assertEqual(html.count('data-dress="women"'), 1)
                self.assertEqual(html.count('data-local-dish'), 2)
                self.assertEqual(html.count('class="th-footer"'), 1)
                self.assertNotIn('أطلس', html)
                self.assertNotIn('الأطلس', html)
                self.assertEqual(response.context['atlas']['extra_gallery'], [])
        # Legacy links resolve to the same local governorate selection.
        self.assertEqual(canonical_key('city:alula'), 'gov:madinah:alula')
        self.assertEqual(profile_for('city:alula')['landmarks'], profile_for('gov:madinah:alula')['landmarks'])


    def test_mahd_replaces_khaybar_in_madinah_selection(self):
        place = Governorate.objects.get(region_key='madinah', slug='mahd-al-dhahab')
        self.assertEqual(place.name, 'مهد الذهب')
        self.assertFalse(Governorate.objects.filter(region_key='madinah', slug='khaybar').exists())
        self.assertEqual(Governorate.objects.count(), 35)
        page = self.client.get('/cities/madinah/')
        self.assertIn(place.get_absolute_url(), page.content.decode())
        self.assertNotIn('/governorates/khaybar/', page.content.decode())
        page = self.client.get(place.get_absolute_url())
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.context['profile']['name'], 'مهد الذهب')
        self.assertNotIn('خيبر', page.content.decode())
        self.assertEqual(self.client.get('/cities/riyadh/governorates/mahd-al-dhahab/').status_code, 404)
        self.client.cookies['saved_cities'] = json.dumps(['gov:madinah:khaybar'])
        self.assertEqual(self.client.get('/cities/', {'saved': 1}).context['result_count'], 0)
        response = self.client.post(place.get_save_url(), HTTP_ACCEPT='application/json')
        self.assertTrue(response.json()['saved'])
        self.assertEqual(response.json()['slug'], 'gov:madinah:mahd-al-dhahab')

    def test_dress_and_food_images_have_valid_local_assets_and_cell_coordinates(self):
        from .content import read_data
        data = read_data('regional_culture.json')
        self.assertEqual(len(data), 13)
        for region, culture in data.items():
            items = [culture['dress']['men'], culture['dress']['women'], *culture['dishes']]
            self.assertEqual(len(items), 4)
            for item in items:
                with self.subTest(region=region, item=item.get('title', item.get('name'))):
                    art = item['illustration']
                    self.assertTrue((settings.BASE_DIR / 'static' / art['file']).is_file())
                    self.assertGreaterEqual(art['x'], 0)
                    self.assertLess(art['x'], art['columns'])
                    self.assertGreaterEqual(art['y'], 0)
                    self.assertLess(art['y'], art['rows'])
                    self.assertEqual(art['type'], 'conceptual-illustration')
                    self.assertLess(art['y']*art['columns'] + art['x'], 11 if 'women' in art['file'] else (9 if 'men' in art['file'] else (10 if 'dishes-b' in art['file'] else 16)))
                    if item.get('image_key'):
                        self.assertIn(item['image_key'], get_media())
        place = Governorate.objects.get(slug='mahd-al-dhahab')
        page = self.client.get(place.get_absolute_url())
        self.assertEqual(page.content.decode().count('<figure class="culture-picture'), 4)
        self.assertContains(page, 'رسم تعريفي تصوّري')
