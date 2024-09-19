from django.forms import ModelForm, HiddenInput
from crispy_forms.helper import FormHelper

from app.models.classes import Class, AcademicClass, Stream, AcademicClassStream,ClassSubjectAllocation
from app.models.staffs import Staff

class ClassForm(ModelForm):
    
    class Meta:
        model = Class
        fields = ("__all__")

class AcademicClassForm(ModelForm):
    
    class Meta:
        model = AcademicClass
        fields = ("__all__")

class StreamForm(ModelForm):
    
    class Meta:
        model = Stream
        fields = ("__all__")

class AcademicClassStreamForm(ModelForm):
    
    class Meta:
        model = AcademicClassStream
        fields = ("__all__")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Helper = FormHelper()
        self.fields["academic_class"].widget = HiddenInput()
        

class ClassSubjectAllocationForm(ModelForm):
    class Meta:
        model = ClassSubjectAllocation
        fields =("__all__")
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Helper = FormHelper()
        self.fields['subject_teacher'].queryset = Staff.objects.filter(department='Academic')
