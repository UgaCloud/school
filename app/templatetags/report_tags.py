from django import template

register = template.Library()

@register.filter
def aggregate_points(report_data, assessment_name):
    

    total = 0
    for item in report_data:

        points = item.get('assessments', {}).get(assessment_name, {}).get('points', None)
        if points is not None and points != '-':
            try:
                total += float(points)
            except (ValueError, TypeError):
                continue
    
    return total if total > 0 else '-'

@register.filter
def lookup(dictionary, key):
    

    return dictionary.get(key, '-') if isinstance(dictionary, dict) else '-'




@register.filter
def get_item(dictionary, key):
    return dictionary.get(str(key), {})



