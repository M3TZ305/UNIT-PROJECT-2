"""Hydrate a sourced place profile while preserving photo attribution order."""
from .content import read_data, get_media
from .place_profiles import apply_profile


def city_atlas(slug):
    atlas = apply_profile(read_data('atlases.json')[slug], 'city:' + slug)
    media = get_media()
    landmarks, credits = [], []
    for raw in atlas['landmarks']:
        image = media.get(raw.get('image_key'))
        entry = {**raw}
        if image:
            entry.update(image=image, gallery_index=len(credits))
            credits.append({key: image[key] for key in ('author', 'license', 'source')})
        landmarks.append(entry)
    atlas.update(landmarks=landmarks, gallery_credits=credits,
                 history_image=media.get(atlas.get('history_image_key')))
    return atlas
