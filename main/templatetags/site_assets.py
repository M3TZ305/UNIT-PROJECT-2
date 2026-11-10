"""Revision URLs prevent browsers retaining an older local stylesheet."""
from pathlib import Path
from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def asset(path):
    url = static(path)
    location = finders.find(path)
    if not location:
        return url
    return f'{url}?v={Path(location).stat().st_mtime_ns}'
