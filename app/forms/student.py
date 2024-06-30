from django.forms import ModelForm, DateInput
from crispy_forms.helper import FormHelper

from app.models.students import Student, ClassRegister, StudentRegistrationCSV

class StudentForm(ModelForm):
    
    class Meta:
        model = Student
        fields = ("__all__")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.Helper = FormHelper()
        self.fields["birthdate"].widget = DateInput(attrs={
                    "type": "date",
                })

class StudentRegistrationCSVForm(ModelForm):
    class Meta:
        model = StudentRegistrationCSV
        fields = ("file_name",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.Helper = FormHelper()

class ClassRegisterForm(ModelForm):
    
    class Meta:
        model = ClassRegister
        fields = ("__all__")
