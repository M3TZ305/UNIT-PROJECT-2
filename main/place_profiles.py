"""Sourced local landmarks and explicitly scoped regional dress and cuisine."""
from copy import deepcopy
from .content import read_data, get_media


def canonical_key(key):
    if key.startswith('city:'):
        slug = key.split(':', 1)[1]
        return read_data('geography.json').get('legacy_city_keys', {}).get(slug, key)
    return key


def profile_for(key):
    profile = deepcopy(read_data('place_profiles.json')[canonical_key(key)])
    profile['culture'] = deepcopy(read_data('regional_culture.json')[profile['region_key']])
    media = get_media()
    items = [profile['culture']['dress']['men'], profile['culture']['dress']['women'], *profile['culture']['dishes']]
    for item in items:
        if item.get('image_key'):
            item['image'] = media[item['image_key']]
    return profile


def source_list(profile):
    culture = profile['culture']
    return [profile['fame']['source'],
            culture['dress']['men']['source'], culture['dress']['women']['source'],
            *culture['dress']['men'].get('additional_sources', []),
            *[item['source'] for item in culture['dishes']],
            *[item['source'] for item in profile['landmarks']]]


def apply_profile(entry, key):
    entry = deepcopy(entry)
    profile = profile_for(key)
    entry['profile'] = profile
    entry['landmarks'] = profile['landmarks']
    # A second gallery must not add modern or out-of-boundary places.
    entry['extra_gallery'] = []
    images = [item['image_key'] for item in entry['landmarks'] if item.get('image_key')]
    if entry.get('history_image_key') not in images:
        entry['history_image_key'] = images[0] if images else None
        entry['history_caption'] = next((item['caption'] for item in entry['landmarks'] if item.get('image_key')), '')
    all_sources = entry.get('sources', []) + source_list(profile)
    entry['sources'] = list({source['url']: source for source in all_sources}.values())
    return entry
