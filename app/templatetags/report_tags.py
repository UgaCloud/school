from django import template

register = template.Library()

@register.filter
def get_item(d, key):
    """
    Safely fetch a dictionary item by dynamic key in Django templates.
    Usage:
      {{ some_dict|get_item:dynamic_key }}
    Falls back to getattr for simple objects.
    """
    try:
        if d is None or key is None:
            return None
        if isinstance(d, dict):
            return d.get(key)
        # Fallback: allow attribute access if not a dict
        return getattr(d, key, None)
    except Exception:
        return None
