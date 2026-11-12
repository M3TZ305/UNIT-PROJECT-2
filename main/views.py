import json
from django.utils.translation import get_language, gettext as _

from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.templatetags.static import static
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .content import get_catalog, get_media, search_key
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
        'site_language': get_language(), 'text_direction': 'rtl' if get_language() == 'ar' else 'ltr',
        'client_messages': {text: _(text) for text in ['أُزيلت المدينة من حكاياتك.', 'احفظ الحكاية', 'تعذّر حفظ الحكاية. جرّب مرة أخرى.', 'تعذّر حفظ الوضع. جرّب مرة أخرى.', 'تفعيل الوضع الليلي', 'تفعيل الوضع النهاري', 'حُفظت الحكاية. تجدها في «حكاياتي».', 'محفوظة']},
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
    region_filter = request.GET.get('region', '')
    if region_filter not in registry()['regions']:
        region_filter = ''
    collection = cultural_topic(topic, region_filter)
    if collection is None:
        raise Http404('Unknown cultural topic')
    food_page = None
    if topic == 'food':
        from django.core.paginator import Paginator
        paginator = Paginator(collection['items'], 12)
        food_page = paginator.get_page(request.GET.get('page'))
        collection['item_count'] = paginator.count
        collection['items'] = list(food_page.object_list)
    return render(request, 'main/culture_topic.html', {
        **common_context(request), 'topic': collection,
        'culture_topics': culture_routes(), 'nav': 'culture',
        'heritage_regions': [{'key': key, 'label': value['label']} for key, value in registry()['regions'].items()],
        'heritage_region': region_filter, 'food_page': food_page,
    })



def city_list(request):
    query = request.GET.get('q', '').strip()[:100]
    directions = [('west', 'المنطقة الغربية'), ('central', 'المنطقة الوسطى'), ('south', 'المنطقة الجنوبية'), ('north', 'المنطقة الشمالية'), ('east', 'المنطقة الشرقية')]
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
    display_order = ['madinah', 'makkah', 'abha'] + [slug for slug in capital_slugs() if slug not in {'madinah', 'makkah', 'abha'}]
    cities = [lookup[slug] for slug in display_order if slug in lookup]
    places = cities
    if only_saved:
        # Saved governorates remain inside their capital city's doorway.
        parent_slugs = set(Governorate.objects.filter(
            pk__in=[g.pk for g in Governorate.objects.all() if g.saved_key in saved]
        ).values_list('capital__slug', flat=True))
        places = [c for c in cities if c.saved_key in saved or c.slug in parent_slugs]
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
        'opening_card': plates[0] if plates else None, 'preview_cards': plates[1:3], 'door_cards': plates[3:],
    })


def atlas_response(request, place):
    from .geography import place_cover
    is_governorate = isinstance(place, Governorate)
    if is_governorate:
        siblings = list(Governorate.objects.select_related('capital').filter(capital=place.capital))
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
        governors = [governorate_plate(g, saved_slugs(request)) for g in place.governorates.select_related('capital')]
    position = next(i for i, item in enumerate(siblings) if item.pk == place.pk)
    return render(request, 'main/city_detail.html', {
        **common_context(request), 'city': place, 'atlas': place.atlas, 'profile': place.atlas['profile'], 'nav': 'cities',
        'is_governorate': is_governorate, 'parent_city': parent, 'region_info': region,
        'directory_slug': parent.slug if parent else (place.slug if place.slug in capital_slugs() else ''),
        'governorate_cards': governors, 'next_city': siblings[(position + 1) % len(siblings)],
        'cover': place_cover(place), 'next_cover': place_cover(siblings[(position + 1) % len(siblings)]),
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
    image = get_media()['about-madinah-1880']
    about_image = {**image, 'url': static(image['fallback'])}
    return render(request, 'main/about.html', {
        **common_context(request), 'about_image': about_image, 'nav': 'about',
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
