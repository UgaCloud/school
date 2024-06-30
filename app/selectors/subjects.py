from app.models.subjects import *

def get_all_subjects():
    return Subject.objects.all()

def get_subject(id):
    return Subject.objects.get(pk=id)