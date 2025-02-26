from app.models.classes import *
from app.models.students import ClassRegister
from app.selectors.school_settings import get_current_academic_year

def get_classes():
    return Class.objects.all()

def get_academic_classes():
    return AcademicClass.objects.all()

def get_academic_class(id):
    return AcademicClass.objects.get(pk=id)

def get_current_academic_class(year, _class, term):
    return AcademicClass.objects.get(academic_year=year, Class=_class, term=term)

def get_academic_class_stream(year, stream):
    return AcademicClassStream.objects.get(academic_class=year, stream=stream)

def get_academic_class_streams(academic_class):
    return AcademicClassStream.objects.filter(academic_class=academic_class)

def get_class_by_code(code):
    return Class.objects.filter(code=code).first()  # Returns None instead of raising an error


def get_stream_by_name(stream):
    return Stream.objects.get(stream=stream)

def get_academic_class_stream_register(academic_class_stream):
    return ClassRegister.objects.filter(academic_class_stream=academic_class_stream)

def get_academic_class_register(academic_class):
    academic_class_streams = get_academic_class_streams(academic_class)
    
    return ClassRegister.objects.filter(academic_class_stream__in=academic_class_streams)

def get_current_academic_year_terms():
    academic_year = get_current_academic_year()
    
    return Term.objects.filter(academic_year=academic_year)

def get_current_term():
    return Term.objects.get(is_current=True)
       