import json

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .content import get_catalog, get_media, search_key, read_data
from .models import City, Governorate
from .geography import capital_slugs, region_for_capital, normalized_saved_keys, city_plate, governorate_plate, matching_plate, registry
from .culture import cultural_topic, culture_routes


def saved_slugs(request):
    try:
        values = json.loads(request.COOKIES.get('saved_cities', '[]'))
    except (ValueError, TypeError):
        return []
    return normalized_saved_keys(values)


def common_context(request):
    theme = request.COOKIES.get('theme', 'light')
    saved = saved_slugs(request)
    return {
        'theme': theme if theme in ('light', 'dark') else 'light',
        'saved_slugs': saved, 'saved_count': len(saved),
        'categories': get_catalog()['categories'],
        'total_cities': len(capital_slugs()), 'total_governorates': registry()['governorate_count'],
    }


def home(request):
    return render(request, 'main/home.html', {
        **common_context(request),
        'nav': 'home',
    })


def culture_topic(request, topic):
    collection = cultural_topic(topic)
    if collection is None:
        raise Http404('Unknown cultural topic')
    return render(request, 'main/culture_topic.html', {
        **common_context(request), 'topic': collection,
        'culture_topics': culture_routes(), 'nav': 'culture',
    })



def city_list(request):
    query = request.GET.get('q', '').strip()[:100]
    directions = [('west', 'الغرب'), ('central', 'الوسط'), ('south', 'الجنوب'), ('north', 'الشمال'), ('east', 'الشرق')]
    region = request.GET.get('region', '')
    if region not in dict(directions):
        region = ''
    category = request.GET.get('category', '')
    if category not in {c['key'] for c in get_catalog()['categories']}:
        category = ''
    province = request.GET.get('province', '')
    if province not in registry()['regions']:
        province = ''
    only_saved = request.GET.get('saved') == '1'
    saved = saved_slugs(request)
    lookup = {c.slug: c for c in City.objects.all()}
    cities = [lookup[slug] for slug in capital_slugs() if slug in lookup]
    places = cities
    if only_saved:
        places = [c for c in cities if c.saved_key in saved]
        places += list(Governorate.objects.select_related('capital').filter(
            pk__in=[g.pk for g in Governorate.objects.all() if g.saved_key in saved]))
        places += [c for c in lookup.values() if c.slug not in capital_slugs() and c.saved_key == c.slug and c.slug in saved]
    plates = []
    matched = []
    for place in places:
        plate = governorate_plate(place, saved) if isinstance(place, Governorate) else city_plate(place, saved)
        if matching_plate(plate, query, region, province) and (not category or category in getattr(place, 'topics', [])):
            plates.append(plate)
            matched.append(place)
    return render(request, 'main/cities.html', {
        **common_context(request), 'cities': matched, 'city_cards': plates,
        'query': query, 'region': region, 'category': category, 'province': province,
        'regions': [{'key': key, 'label': label} for key, label in directions],
        'only_saved': only_saved, 'result_count': len(plates), 'nav': 'cities',
    })


def atlas_response(request, place):
    is_governorate = isinstance(place, Governorate)
    if is_governorate:
        siblings = list(Governorate.objects.filter(capital=place.capital))
        parent = place.capital
        region = region_for_capital(parent.slug)
        governors = []
    else:
        lookup = {c.slug: c for c in City.objects.all()}
        siblings = [lookup[slug] for slug in capital_slugs() if slug in lookup]
        if place.slug not in capital_slugs():
            siblings = list(lookup.values())
        parent = None
        region = region_for_capital(place.slug)
        governors = [governorate_plate(g, saved_slugs(request)) for g in place.governorates.all()]
    position = next(i for i, item in enumerate(siblings) if item.pk == place.pk)
    return render(request, 'main/city_detail.html', {
        **common_context(request), 'city': place, 'atlas': place.atlas, 'nav': 'cities',
        'is_governorate': is_governorate, 'parent_city': parent, 'region_info': region,
        'directory_slug': parent.slug if parent else (place.slug if place.slug in capital_slugs() else ''),
        'governorate_cards': governors, 'next_city': siblings[(position + 1) % len(siblings)],
        'previous_city': siblings[(position - 1) % len(siblings)],
    })


def city_detail(request, slug):
    from .geography import registry
    city = get_object_or_404(City, slug=slug)
    legacy = registry().get('legacy_city_keys', {}).get(slug)
    if legacy:
        _, region, governorate = legacy.split(':')
        place = get_object_or_404(Governorate, region_key=region, slug=governorate)
        return atlas_response(request, place)
    return atlas_response(request, city)


def governorate_detail(request, capital_slug, slug):
    place = get_object_or_404(Governorate.objects.select_related('capital'), capital__slug=capital_slug, slug=slug)
    return atlas_response(request, place)


def about(request):
    return render(request, 'main/about.html', {
        **common_context(request), 'media': {key.replace('-', '_'): value for key, value in get_media().items()}, 'nav': 'about',
    })


def sources(request):
    return render(request, 'main/sources.html', {
        **common_context(request), 'cities': City.objects.all(),
        'culture_sources': list(read_data('culture.json').values()),
        'governorates': Governorate.objects.select_related('capital'), 'credits': get_media().values(), 'illustrations': read_data('design_assets.json'), 'nav': 'sources',
    })


def safe_return(request):
    target = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()},
                                      require_https=request.is_secure()):
        return target
    return reverse('main:home')


@require_POST
def set_theme(request):
    theme = request.POST.get('theme', 'light')
    if theme not in ('light', 'dark'):
        theme = 'light'
    response = (JsonResponse({'theme': theme})
                if request.headers.get('Accept') == 'application/json'
                else redirect(safe_return(request)))
    response.set_cookie('theme', theme, max_age=60 * 60 * 24 * 365,
                        httponly=True, samesite='Lax', secure=request.is_secure())
    return response


@require_POST
def toggle_saved(request, slug):
    place = get_object_or_404(City, slug=slug)
    return save_place(request, place.saved_key)


@require_POST
def toggle_governorate_saved(request, capital_slug, slug):
    place = get_object_or_404(Governorate, capital__slug=capital_slug, slug=slug)
    return save_place(request, place.saved_key)


def save_place(request, slug):
    saved = saved_slugs(request)
    if slug in saved:
        saved.remove(slug)
    else:
        saved.append(slug)
    response = (JsonResponse({'saved': slug in saved, 'count': len(saved), 'slug': slug})
                if request.headers.get('Accept') == 'application/json'
                else redirect(safe_return(request)))
    response.set_cookie('saved_cities', json.dumps(saved), max_age=60 * 60 * 24 * 365,
                        httponly=True, samesite='Lax', secure=request.is_secure())
    return response


def page_not_found(request, exception):
    return render(request, '404.html', common_context(request), status=404)
