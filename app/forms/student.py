from django.forms import ModelForm

from models.students import Student, ClassRegister

class StudentForm(ModelForm):
    
    class Meta:
        model = Student
        fields = ("__all__",)

class ClassRegisterForm(ModelForm):
    
    class Meta:
        model = ClassRegister
        fields = ("__all__",)
