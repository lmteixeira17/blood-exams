"""
Custom template filters and tags for blood exams.
"""

from django import template
from django.contrib.auth.models import User

register = template.Library()


@register.simple_tag(takes_context=True)
def get_impersonated_user(context):
    """Return the impersonated User object, or None."""
    request = context.get('request')
    if request and hasattr(request, 'user') and request.user.is_superuser:
        uid = request.session.get('_impersonate_user_id')
        if uid:
            try:
                return User.objects.get(id=uid)
            except User.DoesNotExist:
                pass
    return None


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key in templates."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def abs_value(value):
    """Return absolute value."""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value


@register.filter
def status_color(value, ref_min_max=None):
    """Return CSS class based on value status."""
    return 'normal'


@register.filter
def trend_icon(pct):
    """Return trend icon based on percentage change."""
    try:
        pct = float(pct)
        if pct > 5:
            return '⬆️'
        elif pct < -5:
            return '⬇️'
        else:
            return '➡️'
    except (ValueError, TypeError):
        return ''
