from django import template

register = template.Library()

@register.filter
def dict_key(dictionary, key):
       """Return the value for the given key from the dictionary."""
       return dictionary.get(key, None)
   