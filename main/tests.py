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
        paths = ['/home/', '/cities/', '/about/', '/culture/architecture/', '/culture/crafts/', '/culture/food/']
        paths += [reverse('main:city_detail', kwargs={'slug': city.slug}) for city in City.objects.all()]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'base.html')
                self.assertNotContains(response, 'src=""')

    def test_root_redirects_to_home(self):
        response = self.client.get('/')
        self.assertRedirects(response, '/home/', fetch_redirect_response=False)

    def test_path_parameter_and_named_url(self):
        url = reverse('main:city_detail', kwargs={'slug': 'jeddah'})
        self.assertEqual(resolve(url).kwargs, {'slug': 'jeddah'})
        self.assertTemplateUsed(self.client.get(url), 'main/city_detail.html')

    def test_home_stays_editorial_without_city_grid(self):
        response = self.client.get('/home/')
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
        self.assertContains(self.client.get('/home/'), 'data-theme="dark"')

    def test_invalid_theme_falls_back(self):
        self.client.cookies['theme'] = 'invalid'
        self.assertContains(self.client.get('/home/'), 'data-theme="light"')
        response = self.client.post('/preferences/theme/', {'theme': 'invalid'})
        self.assertEqual(response.cookies['theme'].value, 'light')

    def test_preference_redirect_rejects_external_url(self):
        for target in ['https://evil.example/', '//evil.example/']:
            response = self.client.post('/preferences/theme/', {'theme': 'dark', 'next': target})
            self.assertEqual(response['Location'], '/home/')

    def test_ajax_theme_response(self):
        response = self.client.post('/preferences/theme/', {'theme': 'dark'}, HTTP_ACCEPT='application/json')
        self.assertEqual(response.json(), {'theme': 'dark'})

    def test_save_remove_and_saved_filter(self):
        url = reverse('main:toggle_saved', kwargs={'slug': 'jeddah'})
        response = self.client.post(url, HTTP_ACCEPT='application/json')
        self.assertEqual(response.json()['count'], 1)
        response = self.client.get('/cities/', {'saved': 1})
        self.assertEqual([city.slug for city in response.context['cities']], ['makkah'])
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
        secure_client.get('/home/')
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
            self.assertTrue(item['url'].startswith(('https://', '/static/')))
            if item['url'].startswith('/static/'):
                self.assertTrue(item.get('prefer_local'))
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
        self.assertEqual({city.slug for city in cities}, set(capital_slugs()))
        self.assertEqual([city.slug for city in cities[:3]], ['madinah', 'makkah', 'abha'])

    def test_administrative_province_filter(self):
        response = self.client.get('/cities/', {'province': 'madinah'})
        self.assertEqual([city.slug for city in response.context['cities']], ['madinah'])
        response = self.client.get('/cities/', {'province': 'not-real'})
        self.assertEqual(response.context['province'], '')

    def test_more_than_six_saved_cities(self):
        from .geography import capital_slugs
        slugs = capital_slugs()[:9]
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
                self.assertTrue(credit['source'].startswith('https://'))

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
        response = self.client.get('/home/')
        for topic in ('architecture', 'crafts', 'food'):
            self.assertContains(response, reverse('main:culture_topic', kwargs={'topic': topic}))
            self.assertNotContains(response, f'?category={topic}')

    def test_culture_routes_present_the_subject_before_the_cities(self):
        expected = {'architecture': 21, 'crafts': 9, 'food': 12}
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
        from .culture import cultural_topic
        for key in ('crafts', 'architecture', 'food'):
            topic = cultural_topic(key)
            keys = [item['key'] for item in topic['items']]
            self.assertEqual(len(keys), len(set(keys)))
            for item in topic['items']:
                self.assertTrue(item['related_places'])
                for place in item['related_places']:
                    self.assertTrue(place['url'].startswith('/cities/'))
                if item.get('photo'):
                    self.assertTrue(item['photo']['source'].startswith('https://'))
                elif item.get('art'):
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
        self.assertEqual(page.context['city_cards'][0]['url'], place.capital.get_absolute_url())
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
                self.assertLessEqual(len(profile['culture']['dishes']), 2)
                self.assertEqual(len({d['name'] for d in profile['culture']['dishes']}), len(profile['culture']['dishes']))
                self.assertLessEqual(len(profile['landmarks']), 5)
                self.assertEqual(len({l['name'] for l in profile['landmarks']}), len(profile['landmarks']))
                for item in profile['landmarks']:
                    self.assertEqual(item['kind'], 'heritage-history')
                    self.assertTrue(item['scope'])
                    self.assertTrue(item['source']['url'].startswith('https://'))
                response = self.client.get(place.get_absolute_url())
                html = response.content.decode()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(html.count('data-dress="men"'), int(bool(profile['culture']['dress']['men'])))
                self.assertEqual(html.count('data-dress="women"'), int(bool(profile['culture']['dress']['women'])))
                self.assertEqual(html.count('data-local-dish'), len(profile['culture']['dishes']))
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

    def test_local_culture_has_evidence_and_never_inherits_parent_data(self):
        from .content import read_data
        from .place_profiles import profile_for, source_list
        from unittest.mock import patch
        data = read_data('local_culture.json')
        self.assertEqual(set(data), set(read_data('place_profiles.json')))
        for key, culture in data.items():
            items = [culture['dress']['men'], culture['dress']['women'], *culture['dishes'], *culture['fruits']]
            for item in filter(None, items):
                self.assertEqual(item['place_key'], key)
                if item in culture['fruits']:
                    self.assertEqual(item['evidence_scope'], 'local')
                elif item in culture['dishes']:
                    self.assertIn(item['evidence_scope'], {'local', 'regional'})
                    if item['evidence_scope'] == 'regional':
                        self.assertEqual(item['scope_label'], 'من مائدة المنطقة المشتركة')
                        self.assertTrue(item['scope_region'])
                else:
                    self.assertIn(item['evidence_scope'], {'local', 'regional', 'national'})
                    self.assertTrue(item['scope_label'])
                self.assertTrue(item['source']['url'].startswith('https://'))
                self.assertTrue(item.get('source_evidence') or item.get('evidence_quote'))
                if item.get('illustration'):
                    art = item['illustration']
                    self.assertTrue((settings.BASE_DIR / 'static' / art['file']).is_file())
                    self.assertLess(art['x'], art['columns'])
                    self.assertLess(art['y'], art['rows'])
            self.assertTrue(source_list(profile_for(key)))
        original = read_data
        def guarded(filename):
            self.assertNotEqual(filename, 'regional_culture.json')
            return original(filename)
        with patch('main.place_profiles.read_data', side_effect=guarded):
            profile = profile_for('city:riyadh')
            self.assertEqual(profile['culture']['dishes'][0]['name'], 'الجريش')
            self.assertEqual(profile['culture']['dishes'][0]['evidence_scope'], 'regional')
            self.assertEqual(profile['culture']['dress']['men']['evidence_scope'], 'regional')
        page = self.client.get('/cities/riyadh/')
        self.assertContains(page, '<figure class="culture-picture', count=3)
        self.assertContains(page, 'data-local-dish', count=1)
        self.assertContains(page, 'data-dish-scope="regional"')
        page = self.client.get('/cities/abha/')
        self.assertContains(page, 'data-local-fruit')
        self.assertContains(page, 'الفراولة')


    def test_cuisine_remains_accessible_and_all_published_dishes_have_visuals(self):
        from .content import read_data
        for culture in read_data('local_culture.json').values():
            for dish in culture['dishes']:
                self.assertTrue(dish.get('image_key') or dish.get('illustration'))
        for place in [*City.objects.all(), *Governorate.objects.select_related('capital')]:
            page = self.client.get(place.get_absolute_url())
            self.assertEqual(page.status_code, 200)
            self.assertContains(page, 'id="dishes"', count=1)
            self.assertContains(page, 'data-cuisine-nav', count=1)
            culture = page.context['profile']['culture']
            self.assertEqual(page.content.decode().count('data-cuisine-pending'), int(not culture['dishes']))
            for landmark in page.context['atlas']['landmarks']:
                if not landmark.get('image'):
                    self.assertTrue(landmark['story'].strip())
                    self.assertNotIn('photo_search_url', landmark)
            self.assertNotContains(page, 'landmark-photo-status')


    def test_every_fruit_has_matching_visual_and_renders_inside_its_card(self):
        from .content import read_data
        expected_cells = {
            'التمور': 0, 'العنب': 1, 'الرمان': 2, 'التين': 3,
            'الفراولة': 4, 'المانجو': 5, 'البرتقال': 6, 'الموز': 7,
            'الليمون': 8, 'المشمش': 9, 'الخوخ': 10, 'السفرجل': 11,
            'الجوافة': 12, 'التمر الهندي': 13, 'تمور الخلاص والرزيز والشيشي': 14,
            'التين الشوكي والتين': 15, 'الموز والبابايا': 16,
            'البرتقال والليمون الحلو': 17, 'العجوة والعنبرة': 18,
        }
        for culture in read_data('local_culture.json').values():
            for fruit in culture['fruits']:
                art = fruit['illustration']
                self.assertTrue((settings.BASE_DIR / 'static' / art['file']).is_file())
                self.assertEqual(art['y'] * art['columns'] + art['x'], expected_cells[fruit['name']])
                self.assertEqual(art['type'], 'conceptual-illustration')
                self.assertLess(art['x'], art['columns'])
                self.assertLess(art['y'], art['rows'])
        for place in [*City.objects.all(), *Governorate.objects.select_related('capital')]:
            page = self.client.get(place.get_absolute_url())
            html = page.content.decode()
            fruits = page.context['profile']['culture']['fruits']
            self.assertEqual(html.count('culture-picture is-fruit'), len(fruits))
            cards = html.split('data-local-fruit>')[1:]
            self.assertEqual(len(cards), len(fruits))
            for card, fruit in zip(cards, fruits):
                card = card.split('</article>', 1)[0]
                self.assertIn('culture-picture is-fruit', card)
                self.assertIn(fruit['name'], card)
                self.assertIn('رسم تعريفي تصوّري', card)


    def test_mahd_cuisine_renders_khawadah_with_its_illustration_and_source(self):
        page = self.client.get('/cities/madinah/governorates/mahd-al-dhahab/')
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'الخواضة')
        self.assertContains(page, 'images/culture/khawadah-v1-cutout.webp')
        self.assertContains(page, 'رسم تعريفي تصوّري')
        self.assertContains(page, 'https://www.okaz.com.sa/local/na/1549969')
        self.assertNotContains(page, 'data-cuisine-pending')
        self.assertEqual(page.content.decode().count('data-local-dish'), 1)
        self.assertEqual(page.context['profile']['culture']['dishes'][0]['place_key'], 'gov:madinah:mahd-al-dhahab')
        self.assertEqual(page.context['profile']['culture']['dress']['men']['evidence_scope'], 'national')
        self.assertEqual(page.context['profile']['culture']['fruits'], [])


    def test_all_places_have_scoped_dress_visuals_without_relabeling_shared_dress_as_local(self):
        from .content import read_data
        data = read_data('local_culture.json')
        self.assertEqual(len(data), 51)
        for key, culture in data.items():
            for sex in ('men', 'women'):
                item = culture['dress'][sex]
                self.assertTrue(item['title'])
                self.assertTrue(item['scope_label'])
                self.assertTrue(item['scope_note'])
                self.assertTrue(item.get('source_evidence') or item.get('evidence_quote'))
                self.assertEqual(item['place_key'], key)
                self.assertTrue(item.get('image_key') or item.get('illustration'))
                art = item.get('illustration')
                if art:
                    self.assertTrue((settings.BASE_DIR / 'static' / art['file']).is_file())
                    self.assertLess(art['x'], art['columns'])
                    self.assertLess(art['y'], art['rows'])
        self.assertEqual(data['gov:jazan:fayfa']['dress']['men']['evidence_scope'], 'local')
        self.assertEqual(data['gov:madinah:mahd-al-dhahab']['dress']['men']['evidence_scope'], 'national')
        self.assertEqual(data['gov:madinah:mahd-al-dhahab']['dress']['women']['evidence_scope'], 'regional')
        for place in [*City.objects.all(), *Governorate.objects.select_related('capital')]:
            page = self.client.get(place.get_absolute_url())
            self.assertContains(page, 'culture-picture is-clothing', count=2)
            self.assertContains(page, 'data-dress-scope=', count=2)
            for item in page.context['profile']['culture']['dress'].values():
                if isinstance(item, dict):
                    self.assertContains(page, item['scope_label'])
                    self.assertContains(page, item['source']['url'])


    def test_landmark_stories_are_complete_without_disclosures(self):
        from .content import read_data
        data = read_data('place_profiles.json')
        total = 0
        for key, profile in data.items():
            for landmark in profile['landmarks']:
                parts = landmark.get('narrative', [])
                self.assertLessEqual(len(parts), 3)
                self.assertEqual(len({part['key'] for part in parts}), len(parts))
                for part in parts:
                    self.assertIn(part['key'], {'story', 'people', 'trace'})
                    self.assertTrue(part['label'].strip())
                    self.assertTrue(part['text'].strip())
                    self.assertTrue(part['source']['url'].startswith('https://'))
                total += bool(parts)
        self.assertGreater(total, 80)
        from django.conf import settings
        media = read_data('media.json')
        for profile in data.values():
            for landmark in profile['landmarks']:
                image = media[landmark['image_key']]
                self.assertTrue((settings.BASE_DIR / 'static' / image['fallback']).is_file())
                self.assertTrue(image['source'].startswith('https://'))
                self.assertTrue(image['author'])
                self.assertTrue(image['license'])
        places = list(City.objects.all()) + list(Governorate.objects.select_related('capital'))
        for place in places:
            with self.subTest(place=place.name):
                response = self.client.get(place.get_absolute_url())
                html = response.content.decode()
                atlas = response.context['atlas']
                landmarks = atlas['landmarks']
                self.assertEqual(response.status_code, 200)
                self.assertLessEqual(len(landmarks), 5)
                self.assertNotIn('<details class="landmark-story">', html)
                self.assertEqual(html.count('class="landmark-story-lead"'), len(landmarks))
                self.assertNotIn('مصدر الحكاية', html)
                self.assertNotIn('من حياة المكان', html)
                self.assertNotIn('href="/sources/"', html)
                sources = {source['url'] for source in atlas['sources']}
                for landmark in landmarks:
                    parts = landmark.get('narrative', [])
                    from django.utils.html import escape
                    self.assertTrue(landmark['story'].strip())
                    self.assertIn(escape(landmark['story']), html)
                    self.assertLessEqual(len(landmark['story'].split()), 100)
                    if landmark.get('image'):
                        self.assertIn(escape(landmark['image']['author']), html)
                        self.assertIn(escape(landmark['image']['license_url']), html)
                    for part in parts:
                        self.assertIn(part['source']['url'], sources)
        makhwah = data['gov:baha:al-makhwah']['landmarks']
        self.assertNotIn('قرية عشم الأثرية', [l['name'] for l in makhwah])

    def test_place_story_details_explain_real_uses(self):
        from .place_profiles import profile_for
        basam = next(l for l in profile_for('gov:qassim:unaizah')['landmarks'] if l['name'] == 'بيت البسام')
        text = ' '.join(p['text'] for p in basam['narrative'])
        self.assertIn('طحن الحبوب', text)
        self.assertIn('مخازن التمر', text)
        mosque = next(l for l in profile_for('gov:qassim:unaizah')['landmarks'] if l['name'] == 'مسجد الجوز')
        self.assertTrue(any(p['key'] == 'people' and 'شتاء' in p['text'] for p in mosque['narrative']))


class CityDoorDirectoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('sync_geography', verbosity=0)

    def test_directory_has_thirteen_unique_city_doorways(self):
        from .content import read_data
        response = self.client.get('/cities/')
        cards = response.context['city_cards']
        self.assertEqual(len(cards), 13)
        self.assertEqual(cards[0]['key'], 'madinah')
        self.assertEqual(response.context['opening_card']['key'], 'madinah')
        self.assertEqual(len(response.context['preview_cards']), 2)
        self.assertEqual(len(response.context['door_cards']), 10)
        self.assertEqual(len({card['caption'] for card in cards}), 13)
        self.assertEqual(set(read_data('city_doors.json')), {card['key'] for card in cards})
        self.assertContains(response, 'class="city-door-window"', count=13)
        for card in cards:
            self.assertEqual(card['kind'], 'city')
            self.assertNotIn('/governorates/', card['url'])
            self.assertTrue(card['image']['source'])
        self.assertNotContains(response, '/governorates/')
        self.assertNotContains(response, 'type="search"')
        from django.conf import settings
        from .content import get_media
        media = get_media()
        for card in cards:
            entry = read_data('city_doors.json')[card['key']]
            self.assertEqual(card['image']['fallback'], media[entry['image_key']]['fallback'])
            self.assertEqual(media[entry['image_key']]['subject_type'], 'cityscape')
            self.assertTrue((settings.BASE_DIR / 'static' / card['image']['fallback']).is_file())
        self.assertContains(response, 'class="doors-opening"')


    def test_regions_keep_city_only_doorways_in_both_languages_and_themes(self):
        from django.conf import settings
        for language in ['ar', 'en']:
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
            for theme in ['light', 'dark']:
                self.client.cookies['theme'] = theme
                for region in ['west', 'central', 'east', 'north', 'south']:
                    with self.subTest(language=language, theme=theme, region=region):
                        page = self.client.get('/cities/', {'region': region})
                        self.assertEqual(page.status_code, 200)
                        self.assertTrue(page.context['city_cards'])
                        self.assertTrue(all(c['direction'] == region and c['kind'] == 'city' for c in page.context['city_cards']))
                        self.assertNotContains(page, '/governorates/')


class PlaceHeritageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('sync_geography', verbosity=0)

    def test_every_canonical_place_has_sourced_crafts_and_architecture(self):
        from .content import read_data
        from .place_profiles import profile_for
        assignments = read_data('place_heritage.json')
        self.assertEqual(set(assignments), set(read_data('place_profiles.json')))
        self.assertEqual(len(assignments), 51)
        for key in assignments:
            heritage = profile_for(key)['heritage']
            for kind in ['crafts', 'architecture']:
                with self.subTest(place=key, kind=kind):
                    self.assertTrue(heritage[kind])
                    for item in heritage[kind]:
                        self.assertTrue(item['source']['url'].startswith('https://'))
                        self.assertTrue(item['intro'])
                        self.assertTrue(item['materials'])
                        self.assertIn(item['evidence_scope'], ['local', 'regional'])
                        if item['evidence_scope'] == 'regional':
                            self.assertTrue(item['scope_note'])
                            self.assertTrue(item['region'])
                        if item.get('image'):
                            self.assertTrue((settings.BASE_DIR / 'static' / item['image']['fallback']).is_file())
                            self.assertTrue(item['caption'])
                        else:
                            self.assertTrue((settings.BASE_DIR / 'static' / item['art']['file']).is_file())
                            self.assertTrue(item['art']['transparent'])

    def test_collections_cover_every_place_without_alias_duplicates(self):
        from .heritage import collection_for
        from .content import read_data
        keys = set(read_data('place_heritage.json'))
        for kind in ['crafts', 'architecture']:
            entries = collection_for(kind)
            self.assertEqual({p['key'] for e in entries for p in e['related_places']}, keys)
            for entry in entries:
                related = entry['related_places']
                self.assertEqual(len(related), len({p['key'] for p in related}))
                self.assertTrue(all(p['url'].endswith('#' + kind) for p in related))

    def test_regional_crafts_do_not_turn_into_false_local_claims(self):
        from .place_profiles import profile_for
        mahd = profile_for('gov:madinah:mahd-al-dhahab')['heritage']['crafts'][0]
        self.assertEqual(mahd['evidence_scope'], 'regional')
        self.assertEqual(profile_for('gov:makkah:al-qunfudhah')['heritage']['crafts'][0]['key'], 'pottery')
        self.assertEqual(profile_for('city:makkah')['heritage']['crafts'][0]['key'], 'kiswa')
        self.assertEqual(profile_for('gov:tabuk:duba')['heritage']['architecture'][0]['key'], 'tabuk-coast')
        self.assertEqual(profile_for('gov:jazan:farasan')['heritage']['architecture'][0]['key'], 'farasan')

    def test_place_sections_and_collection_region_filter_render_in_both_languages(self):
        from django.conf import settings
        for language in ['ar', 'en']:
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
            for url in ['/cities/madinah/', '/cities/madinah/governorates/mahd-al-dhahab/']:
                page = self.client.get(url)
                self.assertContains(page, 'id="crafts"')
                self.assertContains(page, 'id="architecture"')
                self.assertContains(page, '/culture/crafts/#piece-')
                self.assertContains(page, '/culture/architecture/#piece-')
            for kind in ['crafts', 'architecture']:
                page = self.client.get('/culture/' + kind + '/', {'region': 'madinah'})
                self.assertEqual(page.status_code, 200)
                related = [p for e in page.context['topic']['items'] for p in e['related_places']]
                self.assertEqual({p['key'] for p in related}, {'city:madinah', 'gov:madinah:alula', 'gov:madinah:yanbu', 'gov:madinah:mahd-al-dhahab'})


class FoodCollectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('sync_geography', verbosity=0)

    def test_collection_reuses_every_local_food_record_and_exact_artwork(self):
        from .food_collection import food_collection
        from .content import read_data
        collection = food_collection()
        self.assertEqual(len(collection), 38)
        represented = {(row['place_key'], item['food_kind'], item['title'])
                       for item in collection for row in item['place_records']}
        local = read_data('local_culture.json')
        expected = {(key, kind, record['name']) for key, place in local.items()
                    for kind in ['dishes'] for record in place[kind]}
        self.assertEqual(represented, expected)
        for item in collection:
            self.assertFalse(item.get('photo_key'))
            for row in item['place_records']:
                self.assertEqual(item['art'], row['art'])
                original = next(x for x in local[row['place_key']][item['food_kind']] if x['name'] == item['title'])
                self.assertEqual(row['text'], original['text'])
                self.assertEqual(row['source'], original['source'])

    def test_food_filters_preserve_local_links_and_reused_cutouts(self):
        from django.conf import settings
        for language in ['ar', 'en']:
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
            for kind, count in [('dishes', 12), ('fruits', 12)]:
                page = self.client.get('/culture/food/', {'type': kind})
                self.assertEqual(page.status_code, 200)
                items = page.context['topic']['items']
                self.assertEqual(len(items), count)
                self.assertTrue(all(item['food_kind'] == 'dishes' for item in items))
                self.assertNotContains(page, 'food-collection-tabs')
                self.assertContains(page, '-cutout.webp')
            page = self.client.get('/culture/food/', {'type': 'dishes', 'region': 'madinah'})
            related = [p for item in page.context['topic']['items'] for p in item['related_places']]
            self.assertTrue(related)
            self.assertTrue(all(p['key'] == 'city:madinah' or p['key'].startswith('gov:madinah:') for p in related))
            self.assertContains(page, 'khawadah-v1-cutout.webp')


class CompletedPlaceTableTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('sync_geography', verbosity=0)

    def test_every_place_has_a_sourced_visual_dish_and_shared_food_is_marked(self):
        from .content import read_data
        data = read_data('local_culture.json')
        self.assertEqual(len(data), 51)
        for key, place in data.items():
            with self.subTest(place=key):
                self.assertTrue(place['dishes'])
                self.assertLessEqual(len(place['dishes']), 2)
                for dish in place['dishes']:
                    self.assertEqual(dish['place_key'], key)
                    self.assertTrue(dish['source']['url'].startswith('https://'))
                    self.assertTrue(dish.get('source_evidence') or dish.get('evidence_quote'))
                    self.assertTrue(dish['illustration']['transparent'])
                    self.assertTrue((settings.BASE_DIR / 'static' / dish['illustration']['file']).is_file())
                    if dish['evidence_scope'] == 'regional':
                        self.assertTrue(dish['scope_label'])
                        self.assertTrue(dish['scope_region'])
        self.assertEqual(data['city:hafar-al-batin']['dishes'][0]['name'], 'أذان الشايب')
        self.assertEqual(data['gov:madinah:mahd-al-dhahab']['dishes'][0]['name'], 'الخواضة')

    def test_food_pagination_covers_collection_once_and_respects_region(self):
        from .food_collection import food_collection
        expected = {e['key'] for e in food_collection()}
        seen = []
        first = self.client.get('/culture/food/')
        self.assertEqual(first.context['topic']['item_count'], len(expected))
        for number in first.context['food_page'].paginator.page_range:
            page = self.client.get('/culture/food/', {'page': number})
            items = page.context['topic']['items']
            self.assertLessEqual(len(items), 12)
            seen.extend(item['key'] for item in items)
        self.assertEqual(set(seen), expected)
        self.assertEqual(len(seen), len(expected))
        self.assertEqual(self.client.get('/culture/food/', {'page': 'bad'}).context['food_page'].number, 1)
        self.assertEqual(self.client.get('/culture/food/', {'page': 999}).context['food_page'].number, first.context['food_page'].paginator.num_pages)


class GovernorateCoverConsistencyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('sync_geography', verbosity=0)

    def test_every_governorate_card_matches_its_current_opening(self):
        from .geography import governorate_plate
        for place in Governorate.objects.select_related('capital'):
            with self.subTest(place=place.slug):
                card = governorate_plate(place, [])
                cover = place.atlas
                self.assertEqual(card['image'], cover['history_image'])
                self.assertEqual(card['image_caption'], cover['history_caption'])
                self.assertEqual(place.data['hero'], cover['history_image'])
                self.assertFalse(card['is_map'])
                if card['image']:
                    self.assertContains(self.client.get(place.capital.get_absolute_url()), card['image']['url'])
                    self.assertContains(self.client.get(place.get_absolute_url()), card['image']['url'])
                else:
                    self.assertEqual(card['art'], place.data['chapter_art'])

class ExhibitionRefinementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('sync_geography', verbosity=0)

    def test_place_heritage_can_be_read_without_javascript(self):
        from html.parser import HTMLParser
        class Disclosures(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids = set()
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'details' and 'heritage-disclosure' in attrs.get('class', ''):
                    self.ids.add(attrs.get('id'))
        response = self.client.get('/cities/madinah/')
        parser = Disclosures()
        parser.feed(response.content.decode())
        self.assertTrue({'crafts', 'architecture', 'dishes', 'dress'} <= parser.ids)
        self.assertContains(response, 'href="#dress"')
        self.assertContains(response, 'data-dress="men"')
        self.assertContains(response, 'data-local-dish')

    def test_responsive_photos_have_existing_smaller_variants(self):
        from .content import read_data
        entries = read_data('responsive_images.json')
        self.assertTrue(entries)
        root = settings.BASE_DIR / 'static'
        for original, variants in entries.items():
            self.assertTrue((root / original).is_file())
            for item in variants:
                self.assertTrue((root / item['file']).is_file())
                self.assertIn(item['width'], (640, 1280))
        self.assertTrue(any(image.get('srcset') for image in get_media().values()))


class PlaceIdentityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('sync_geography', verbosity=0)

    def test_directory_opening_and_next_place_share_the_same_image(self):
        from html.parser import HTMLParser
        from .geography import place_cover, city_plate, governorate_plate, registry
        class CoverImages(HTMLParser):
            def __init__(self):
                super().__init__()
                self.role = None
                self.images = {}
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'figure':
                    self.role = attrs.get('class')
                if tag == 'img' and self.role in ('place-cover-photo', 'atlas-next-cover'):
                    self.images[self.role] = attrs['src']
            def handle_endtag(self, tag):
                if tag == 'figure':
                    self.role = None
        cities = City.objects.exclude(slug__in=registry()['legacy_city_keys'])
        places = [*cities, *Governorate.objects.select_related('capital')]
        for place in places:
            with self.subTest(place=place.saved_key):
                cover = place_cover(place)
                card = governorate_plate(place, []) if isinstance(place, Governorate) else city_plate(place, [])
                self.assertEqual(card['image'], cover['image'])
                self.assertEqual(place.data['hero'], cover['image'])
                response = self.client.get(place.get_absolute_url())
                self.assertTrue(place.summary.strip())
                self.assertContains(response, 'class="place-overview-summary"')
                self.assertContains(response, 'id="place-intro-title"')
                self.assertContains(response, place.summary, html=False)
                if response.context['profile']['culture'].get('fruits'):
                    self.assertContains(response, '<section class="place-fruits" id="fruits"')
                    self.assertNotContains(response, '<details class="heritage-disclosure place-fruits"')
                parsed = CoverImages()
                parsed.feed(response.content.decode())
                if cover['image']:
                    self.assertEqual(parsed.images['place-cover-photo'], cover['image']['url'])
                following = response.context['next_cover']
                if following['image']:
                    self.assertEqual(parsed.images['atlas-next-cover'], following['image']['url'])
