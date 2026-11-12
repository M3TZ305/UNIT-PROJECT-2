"""One explicit craft/architecture registry shared by place pages and subject collections."""
from copy import deepcopy
from .content import read_data, get_media


def _hydrate(kind, assignment, region_key, media):
    item = deepcopy(read_data('heritage_catalog.json')[kind][assignment['id']])
    item['evidence_scope'] = assignment['scope']
    item['region_key'] = region_key
    item['region'] = read_data('geography.json')['regions'][region_key]['label']
    item['reference_source'] = item['source']
    item['source'] = assignment.get('source', item['source'])
    item['scope_label'] = ('ممارسة موثّقة في المكان' if kind == 'crafts' else 'نموذج محلي') if assignment['scope'] == 'local' else ('حرفة إقليمية مشتركة' if kind == 'crafts' else 'سياق معماري إقليمي')
    item['scope_note'] = '' if assignment['scope'] == 'local' else ('حرفة مشتركة مع المنطقة، وليست خاصة بهذا المكان وحده.' if kind == 'crafts' else 'سياق من عمارة المنطقة؛ تختلف الأنماط داخل المدينة والمحافظة.')
    if item.get('photo_key'):
        item['image'] = media[item['photo_key']]
    return item


def heritage_for(key, media=None):
    assignments = read_data('place_heritage.json')[key]
    region = read_data('place_profiles.json')[key]['region_key']
    media = get_media() if media is None else media
    return {kind: [_hydrate(kind, item, region, media) for item in assignments[kind]]
            for kind in ('crafts', 'architecture')}


def collection_for(kind, region=''):
    from .models import City, Governorate
    # Canonical keys prevent aliases from displaying a governorate twice.
    places = {'city:' + city.slug: city for city in City.objects.all()}
    places.update({place.saved_key: place for place in Governorate.objects.select_related('capital')})
    profiles = read_data('place_profiles.json')
    grouped = {}
    media = get_media()
    for key, assignments in read_data('place_heritage.json').items():
        place = places.get(key)
        if place is None or (region and profiles[key]['region_key'] != region):
            continue
        for assignment in assignments[kind]:
            item_id = assignment['id']
            if item_id not in grouped:
                item = deepcopy(read_data('heritage_catalog.json')[kind][item_id])
                item.update(related_places=[], regions=[], region='')
                grouped[item_id] = item
            item = grouped[item_id]
            label = read_data('geography.json')['regions'][profiles[key]['region_key']]['label']
            if label not in item['regions']:
                item['regions'].append(label)
            item['related_places'].append({
                'key': key, 'name': place.name,
                'url': place.get_absolute_url() + ('#crafts' if kind == 'crafts' else '#architecture'),
                'scope': assignment['scope'], 'source': assignment.get('source', item['source']),
            })
    result = []
    photo_index = 0
    for item in grouped.values():
        item['region'] = ' · '.join(item['regions'])
        if item.get('photo_key'):
            item.update(photo=media[item['photo_key']], gallery_index=photo_index)
            photo_index += 1
        result.append(item)
    return result
