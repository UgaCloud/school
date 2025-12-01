from app.models.students import *

def get_all_students():
    return Student.objects.all()

def get_student(id):
    return Student.objects.get(pk=id)
    

def get_active_students():
    """
    Active = has a ClassRegister in the current academic year and term.
    Zero schema change; purely selector-based.
    """
    from app.selectors.school_settings import get_current_academic_year
    from app.selectors.classes import get_current_term

    current_year = get_current_academic_year()
    current_term = get_current_term()

    return Student.objects.filter(
        classregister__academic_class_stream__academic_class__academic_year=current_year,
        classregister__academic_class_stream__academic_class__term=current_term,
    ).distinct()


def get_inactive_students():
    """
    Inactive = NO ClassRegister in the current academic year and term.
    """
    from app.selectors.school_settings import get_current_academic_year
    from app.selectors.classes import get_current_term

    current_year = get_current_academic_year()
    current_term = get_current_term()

    return Student.objects.exclude(
        classregister__academic_class_stream__academic_class__academic_year=current_year,
        classregister__academic_class_stream__academic_class__term=current_term,
    ).distinct()