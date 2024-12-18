from django.forms import ModelForm, DateInput
from crispy_forms.helper import FormHelper

from django import forms
from app.models import  AcademicClassStream

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

class BulkStudentRegistrationForm(forms.Form):
    academic_class_stream = forms.ModelChoiceField(
        queryset=AcademicClassStream.objects.all(),
        label="Class Stream",
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    student_ids = forms.CharField(
        label="Student IDs (comma-separated)",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    def clean_student_ids(self):
        ids = self.cleaned_data["student_ids"]
        student_ids = [id.strip() for id in ids.split(",") if id.strip()]
        valid_students = Student.objects.filter(reg_no__in=student_ids)
        if not valid_students.exists():
            raise forms.ValidationError("None of the student IDs are valid.")
        return valid_students

