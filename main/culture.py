"""Hydrate cultural subjects from JSON, keeping views and templates shared."""
from .content import read_data, get_media
from .models import City


def culture_routes():
    return [{key: topic[key] for key in ('key', 'title', 'number')}
            for topic in read_data('culture.json').values()]


def cultural_topic(key):
    raw = read_data('culture.json').get(key)
    if raw is None:
        return None
    media = get_media()
    city_map = {city.slug: city for city in City.objects.filter(
        slug__in={slug for item in raw['items'] for slug in item['cities']})}
    items, photo_index = [], 0
    for entry in raw['items']:
        item = {**entry, 'related_cities': [city_map[slug] for slug in entry['cities'] if slug in city_map]}
        if entry.get('photo_key'):
            item.update(photo=media[entry['photo_key']], gallery_index=photo_index)
            photo_index += 1
        items.append(item)
    return {**raw, 'items': items}
