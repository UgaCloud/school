from app.models.classes import *

def get_classes():
    return Class.objects.all()

def get_academic_classes():
    return AcademicClass.objects.all()
    