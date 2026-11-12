"""Activate the explicit visitor preference, with Arabic as the default."""
from django.conf import settings
from django.utils import translation
from django.utils.cache import patch_vary_headers


class SiteLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME, settings.LANGUAGE_CODE)
        if language not in dict(settings.LANGUAGES):
            language = settings.LANGUAGE_CODE
        request.LANGUAGE_CODE = language
        with translation.override(language):
            response = self.get_response(request)
        response.setdefault('Content-Language', language)
        patch_vary_headers(response, ('Cookie',))
        return response
