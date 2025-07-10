from django import template

register = template.Library()

@register.filter
def get_student_count(student_name, student_name_counts):
    return student_name_counts.get(student_name, 0)

