from django import template

register = template.Library()

@register.filter
def get_entry(timetable_dict, key_tuple):
    return timetable_dict.get(key_tuple)
