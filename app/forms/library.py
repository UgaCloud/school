from django import forms

from app.models import LibraryBook, LibraryCopy


class LibraryBookForm(forms.ModelForm):
    class Meta:
        model = LibraryBook
        fields = "__all__"


class LibraryCopyForm(forms.ModelForm):
    class Meta:
        model = LibraryCopy
        fields = "__all__"


class LibraryIssueForm(forms.Form):
    copy = forms.ModelChoiceField(queryset=LibraryCopy.objects.none())
    student_id = forms.IntegerField(required=False)
    staff_id = forms.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["copy"].queryset = LibraryCopy.objects.filter(
            status=LibraryCopy.STATUS_AVAILABLE
        ).select_related("book")

    def clean(self):
        data = super().clean()
        if bool(data.get("student_id")) == bool(data.get("staff_id")):
            raise forms.ValidationError("Choose exactly one student or staff borrower.")
        return data


class LibraryReturnForm(forms.Form):
    condition = forms.ChoiceField(choices=(("good", "Good"), ("damaged", "Damaged")))
    damage_amount = forms.DecimalField(required=False, min_value=0, decimal_places=2)
    notes = forms.CharField(required=False, max_length=500)

    def clean(self):
        data = super().clean()
        if data.get("condition") == "damaged" and data.get("damage_amount") is None:
            self.add_error("damage_amount", "Enter the approved damage charge, including zero when no charge applies.")
        return data


class LibraryLostForm(forms.Form):
    amount = forms.DecimalField(min_value=0, decimal_places=2, label="Replacement charge")
    notes = forms.CharField(required=False, max_length=500)
