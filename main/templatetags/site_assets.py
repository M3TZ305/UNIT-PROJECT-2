"""Revision URLs prevent browsers retaining an older local stylesheet."""
from pathlib import Path
from django import template
from django.utils.translation import gettext, get_language
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def asset(path):
    from main.media_delivery import cdn_url
    remote = cdn_url(path) if str(path).startswith('images/') else None
    if remote:
        return remote
    url = static(path)
    location = finders.find(path)
    if not location:
        return url
    return f'{url}?v={Path(location).stat().st_mtime_ns}'


@register.filter
def localize(value, context=None):
    """Translate editorial strings without altering IDs, numbers or structures."""
    if not isinstance(value, str):
        return value
    if context == 'landmark' and value == 'الحجر' and get_language() == 'en':
        return gettext('الحِجر — هَجْرا')
    translated = gettext(value)
    if translated == value and ' · ' in value:
        return ' · '.join(gettext(part) for part in value.split(' · '))
    return translated
