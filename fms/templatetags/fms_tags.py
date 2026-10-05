from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Template filter: {{ dict|get_item:key }} -> dict[key]."""
    try:
        return dictionary.get(key)
    except AttributeError:
        return None
