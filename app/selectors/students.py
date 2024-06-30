from app.models.students import *

def get_all_students():
    return Student.objects.all()

def get_student(id):
    return Student.objects.get(pk=id)
    