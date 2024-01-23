from django.forms import ModelForm

from models.classes import Class, AcademicClass, Stream

class ClassForm(ModelForm):
    
    class Meta:
        model = Class
        fields = ("__all__",)

class AcademicClassForm(ModelForm):
    
    class Meta:
        model = AcademicClass
        fields = ("__all__",)

class StreamForm(ModelForm):
    
    class Meta:
        model = Stream
        fields = ("__all__",)
