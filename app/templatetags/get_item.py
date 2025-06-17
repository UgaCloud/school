from django import template

register = template.Library()

@register.simple_tag
def get_item(dictionary, key1, key2):
    return dictionary.get((key1, key2))
