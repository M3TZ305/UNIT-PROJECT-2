"""One documented hierarchy for cities, governorates, search and saved places."""
from copy import deepcopy
from django.urls import reverse
from .content import read_data, get_catalog, get_media, search_key


def registry():
    return read_data('geography.json')


def capital_slugs():
    return registry()['capital_slugs']


def region_for_capital(slug):
    return next((r for r in registry()['regions'].values() if r['capital_slug'] == slug), None)


def record_for_governorate(region_key, slug):
    return read_data('governorates.json')[f'{region_key}:{slug}']


def normalized_saved_keys(values):
    if not isinstance(values, list):
        return []
    legacy = registry().get('legacy_city_keys', {})
    valid = set(get_catalog()['cities']) | {
        'gov:' + key for key in read_data('governorates.json')}
    result = []
    for value in values:
        if not isinstance(value, str):
            continue
        value = legacy.get(value, value)
        if value in valid and value not in result:
            result.append(value)
    return result


def governorate_data(place):
    raw = record_for_governorate(place.region_key, place.slug)
    media = get_media()
    legacy = get_catalog()['cities'].get(raw.get('legacy_city_slug'), {})
    return {
        'name_lines': [place.name], 'chapter_art': raw['art'],
        'tagline': raw['tagline'], 'intro': raw['intro'],
        'hero': media.get(raw.get('image_key')),
        'video': legacy.get('video'), 'sources': raw['sources'],
    }


def governorate_atlas(place):
    raw = deepcopy(record_for_governorate(place.region_key, place.slug))
    media = get_media()
    atlas = raw['atlas']
    credits, landmarks = [], []
    for entry in atlas['landmarks']:
        image = media.get(entry.get('image_key'))
        if image:
            entry.update(image=image, gallery_index=len(credits))
            credits.append({k: image[k] for k in ('author', 'license', 'source')})
        landmarks.append(entry)
    extras = []
    for entry in atlas.get('extra_gallery', []):
        image = media.get(entry.get('key'))
        if image:
            extras.append({**image, 'caption': entry['caption'], 'gallery_index': len(credits)})
            credits.append({k: image[k] for k in ('author', 'license', 'source')})
    atlas.update(landmarks=landmarks, extra_gallery=extras, gallery_credits=credits,
                 history_image=media.get(raw.get('image_key')),
                 history_caption=raw.get('image_caption', ''),
                 intro=raw['intro'], sources=raw['sources'])
    for field in ('heritage_picture', 'food_picture'):
        picture = atlas.get(field, {})
        if picture.get('image_key'):
            picture['image'] = media[picture['image_key']]
    return atlas


def city_plate(city, saved):
    region = region_for_capital(city.slug)
    names = [g['name'] for g in region['governorates']] if region else []
    data = city.data
    return {
        'key': city.slug, 'name': city.name, 'kind': 'city', 'kind_label': 'مدينة',
        'url': city.get_absolute_url(), 'save_url': city.get_save_url(),
        'number': city.number, 'region': city.region, 'province': data.get('province', ''),
        'direction': city.region_key, 'art': data['chapter_art'],
        'image': None, 'caption': data['tagline'], 'saved': city.slug in saved,
        'governorate_count': len(names), 'governorate_names': ' · '.join(names),
        'search': search_key(' '.join([city.name, city.english_name, city.region, *names, *[g['slug'].replace('-', ' ') for g in (region['governorates'] if region else [])]])),
    }


def governorate_plate(place, saved):
    raw = record_for_governorate(place.region_key, place.slug)
    return {
        'key': place.saved_key, 'name': place.name, 'kind': 'governorate',
        'kind_label': 'محافظة', 'url': place.get_absolute_url(),
        'save_url': place.get_save_url(), 'number': place.number,
        'region': place.region, 'province': place.region_key,
        'direction': raw['direction'], 'art': raw['art'],
        'image': get_media().get(raw.get('image_key')), 'is_map': raw.get('image_is_map', False),
        'image_caption': raw.get('image_caption', ''), 'caption': raw['tagline'],
        'saved': place.saved_key in saved,
        'search': search_key(' '.join([place.name, place.english_name, place.region, *raw.get('aliases', [])])),
    }


def matching_plate(plate, query='', direction='', province='', only_saved=False):
    return ((not query or search_key(query) in plate['search'])
            and (not direction or plate['direction'] == direction)
            and (not province or plate['province'] == province)
            and (not only_saved or plate['saved']))
