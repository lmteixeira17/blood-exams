"""
Custom template filters for blood exams.
"""

from django import template

register = template.Library()


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
