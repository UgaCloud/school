from django import forms

from app.models import ParentAccess


class ParentLoginForm(forms.Form):
    phone = forms.CharField(max_length=50, label="Registered guardian phone")
    password = forms.CharField(widget=forms.PasswordInput)


class ParentFirstPasswordForm(forms.Form):
    password = forms.CharField(min_length=8, widget=forms.PasswordInput, label="New password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("confirm_password"):
            self.add_error("confirm_password", "Passwords do not match.")
        if data.get("password") == "123":
            self.add_error("password", "Choose a private password instead of the temporary password.")
        return data


class ParentAccessPermissionsForm(forms.ModelForm):
    class Meta:
        model = ParentAccess
        fields = ("can_view_academics", "can_view_finance", "can_view_attendance")
