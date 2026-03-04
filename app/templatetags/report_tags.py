from django import template
import re

register = template.Library()


_SUBJECT_AR_MAP = {
    "quranrecitation": "القرآن الكريم",
    "quranmemorization": "حفظ القرآن",
    "quran": "القرآن الكريم",
    "tarbiamalezi": "التربية",
    "tarbia": "التربية",
    "fiqh": "الفقه",
    "lughaarabia": "اللغة العربية",
    "arabic": "اللغة العربية",
    "arabiclanguage": "اللغة العربية",
    "english": "اللغة الإنجليزية",
    "mathematics": "الرياضيات",
    "math": "الرياضيات",
    "science": "العلوم",
    "socialstudies": "الدراسات الاجتماعية",
    "socialstudy": "الدراسات الاجتماعية",
    "reading": "القراءة",
    "religiouseducation": "التربية الدينية",
    "islamicstudies": "الدراسات الإسلامية",
}


def _subject_key(subject_name):
    text = str(subject_name or "").strip().lower()
    text = text.replace("'", "")
    text = text.replace("’", "")
    return re.sub(r"[^a-z0-9]+", "", text)


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


@register.filter
def subject_ar(subject_name):
    """Map common subject labels to Arabic and fallback to original text."""
    key = _subject_key(subject_name)
    if not key:
        return "-"
    return _SUBJECT_AR_MAP.get(key, str(subject_name))


@register.filter
def remark_ar(avg_value):
    """Return Arabic performance remark from numeric average score."""
    try:
        avg = float(avg_value)
    except (TypeError, ValueError):
        return "-"

    if avg <= 49:
        return "يحتاج إلى تحسين"
    if avg <= 59:
        return "مبشر"
    if avg <= 69:
        return "متوسط"
    if avg <= 79:
        return "جيد"
    if avg <= 89:
        return "أحسنت"
    if avg <= 100:
        return "ممتاز"
    return "-"
