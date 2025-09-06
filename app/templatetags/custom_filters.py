from django import template

register = template.Library()

@register.filter
def dict_key(dictionary, key):
    """Return the value for the given key from the dictionary."""
    return dictionary.get(key, None)

@register.filter
def get_item(dictionary, key):
    """Safely return the value for the given key from a dictionary."""
    if not isinstance(dictionary, dict):
        return None  # Return None if the input is not a dictionary
    return dictionary.get(str(key), None)  # Safely get the value or None

@register.filter
def not_reserved_key(value):
    return value not in ['total_final_score', 'total_points', 'student_id', 'student_name']

@register.filter
def is_top_score(score, subject_scores):
    """
    Check if the score is the highest among all students for the given subject_scores.
    `subject_scores` is expected to be a list of scores.
    """
    try:
        score = float(score)
        max_score = max([float(s) for s in subject_scores if s is not None])
        return score == max_score
    except:
        return False

@register.filter
def get_score(student, subject):
    return student.get(subject, 0)  # Note: This assumes student is a dict