"""The food collection reuses the exact locally sourced records and artwork of place pages."""
from copy import deepcopy
from hashlib import sha1
from .content import read_data, get_media
from .models import City, Governorate


def food_collection(region=''):
    places = {'city:' + city.slug: city for city in City.objects.all()}
    places.update({p.saved_key: p for p in Governorate.objects.select_related('capital')})
    profiles = read_data('place_profiles.json')
    groups = {}
    media = get_media()
    for key, culture in read_data('local_culture.json').items():
        place = places.get(key)
        if place is None or (region and profiles[key]['region_key'] != region):
            continue
        for kind in ['dishes']:
            for record in culture[kind]:
                identity = (kind, record['name'])
                if identity not in groups:
                    item = {
                        'key': 'food-' + sha1((kind + ':' + record['name']).encode()).hexdigest()[:12],
                        'title': record['name'], 'caption': record['name'],
                        'intro': record['text'], 'materials': [], 'steps': [],
                        'source': deepcopy(record['source']), 'art': deepcopy(record.get('illustration')),
                        'photo_key': None if record.get('illustration') else record.get('image_key'), 'food_kind': kind,
                        'related_places': [], 'place_records': [], 'regions': [],
                    }
                    groups[identity] = item
                item = groups[identity]
                label = read_data('geography.json')['regions'][profiles[key]['region_key']]['label']
                if label not in item['regions']:
                    item['regions'].append(label)
                item['related_places'].append({'key': key, 'name': place.name,
                    'url': place.get_absolute_url() + ('#dishes' if kind == 'dishes' else '#fruits'),
                    'scope': record['evidence_scope']})
                item['place_records'].append({'name': place.name, 'text': record['text'],
                    'source': deepcopy(record['source']), 'art': deepcopy(record.get('illustration')),
                    'place_key': key})
    result, photo_index = [], 0
    for item in groups.values():
        item['region'] = ' · '.join(item['regions'])
        # Place-specific descriptions stay with their place, rather than being generalized.
        if len(item['place_records']) > 1:
            item['intro'] = ''
        if item.get('photo_key'):
            item.update(photo=media[item['photo_key']], gallery_index=photo_index)
            photo_index += 1
        result.append(item)
    return result
