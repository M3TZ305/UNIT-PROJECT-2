"""Hydrate cultural subjects from JSON, keeping views and templates shared."""
from .content import read_data


def culture_routes():
    return [{key: topic[key] for key in ('key', 'title', 'number')}
            for topic in read_data('culture.json').values()]


def cultural_topic(key, region=''):
    raw = read_data('culture.json').get(key)
    if raw is None:
        return None
    if key == 'food':
        from .food_collection import food_collection
        return {**raw, 'items': food_collection(region), 'place_collection': True, 'food_collection': True}
    if key in ('crafts', 'architecture'):
        from .heritage import collection_for
        return {**raw, 'items': collection_for(key, region), 'place_collection': True}
    return None
