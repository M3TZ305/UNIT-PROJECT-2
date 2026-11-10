"""Hydrate one city's JSON atlas, without duplicating view or template logic."""
from .content import read_data, get_media


def city_atlas(slug):
    entry = read_data('atlases.json')[slug]
    media = get_media()
    atlas = {**entry}
    landmarks, credits = [], []
    for raw in entry['landmarks']:
        image = media[raw['image_key']]
        landmarks.append({**raw, 'image': image, 'gallery_index': len(credits)})
        credits.append({key: image[key] for key in ('author', 'license', 'source')})
    extras = []
    for raw in entry.get('extra_gallery', []):
        image = media[raw['key']]
        extras.append({**image, 'caption': raw['caption'], 'gallery_index': len(credits)})
        credits.append({key: image[key] for key in ('author', 'license', 'source')})
    atlas.update(landmarks=landmarks, extra_gallery=extras,
                 gallery_credits=credits, history_image=media[entry['history_image_key']])
    return atlas
