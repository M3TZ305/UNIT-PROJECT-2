import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .content import get_catalog, get_media, search_key
from .models import City


def saved_slugs(request):
    try:
        values = json.loads(request.COOKIES.get('saved_cities', '[]'))
    except (ValueError, TypeError):
        return []
    if not isinstance(values, list):
        return []
    valid = get_catalog()['cities']
    return list(dict.fromkeys(value for value in values
                             if isinstance(value, str) and value in valid))[:6]


def common_context(request):
    theme = request.COOKIES.get('theme', 'light')
    saved = saved_slugs(request)
    return {
        'theme': theme if theme in ('light', 'dark') else 'light',
        'saved_slugs': saved, 'saved_count': len(saved),
        'categories': get_catalog()['categories'],
    }


def home(request):
    return render(request, 'main/home.html', {
        **common_context(request),
        'featured': get_object_or_404(City, slug='jeddah'),
        'media': {key.replace('-', '_'): value for key, value in get_media().items()}, 'nav': 'home',
    })


def city_list(request):
    query = request.GET.get('q', '').strip()[:100]
    category = request.GET.get('category', '')
    region = request.GET.get('region', '')
    only_saved = request.GET.get('saved') == '1'
    catalog = get_catalog()
    if category not in [item['key'] for item in catalog['categories']]:
        category = ''
    regions = [{'key': 'west', 'label': 'الغرب'}, {'key': 'central', 'label': 'الوسط'},
               {'key': 'south', 'label': 'الجنوب'}, {'key': 'north', 'label': 'الشمال'},
               {'key': 'east', 'label': 'الشرق'}]
    if region not in [item['key'] for item in regions]:
        region = ''
    cities = City.objects.all()
    if region:
        cities = cities.filter(region_key=region)
    if only_saved:
        cities = cities.filter(slug__in=saved_slugs(request))
    cities = [city for city in cities if not category or category in city.topics]
    if query:
        term = search_key(query)
        cities = [city for city in cities if term in search_key(
            ' '.join([city.name, city.english_name, city.region, city.summary]))]
    return render(request, 'main/cities.html', {
        **common_context(request), 'cities': cities, 'query': query,
        'category': category, 'region': region, 'regions': regions,
        'only_saved': only_saved, 'result_count': len(cities), 'nav': 'cities',
    })


def city_detail(request, slug):
    city = get_object_or_404(City, slug=slug)
    cities = list(City.objects.all())
    position = next(i for i, item in enumerate(cities) if item.pk == city.pk)
    return render(request, 'main/city_detail.html', {
        **common_context(request), 'city': city, 'nav': 'cities',
        'next_city': cities[(position + 1) % len(cities)],
        'previous_city': cities[(position - 1) % len(cities)],
    })


def about(request):
    return render(request, 'main/about.html', {
        **common_context(request), 'media': {key.replace('-', '_'): value for key, value in get_media().items()}, 'nav': 'about',
    })


def sources(request):
    return render(request, 'main/sources.html', {
        **common_context(request), 'cities': City.objects.all(),
        'credits': get_media().values(), 'nav': 'sources',
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
    get_object_or_404(City, slug=slug)
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
