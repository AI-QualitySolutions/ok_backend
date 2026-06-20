# authentication/forms.py
from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from authentication.models import MyUser, Company
# Import CameraType if it's in a different app
from camera.models import CameraType
from tent.models import Tent  # Import Tent if it's in a different app


class MyUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(
        label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = MyUser
        fields = (
            'email', 'username', 'company', 'is_admin', 'is_active', 'is_staff', 'is_temperature', 'is_guard', 'is_peoplecount', 'is_kitchen', 'is_aggf', 'is_falldetection', 'is_violencedetection', 'is_crowdmonitoring',  'is_climbmonitoring', 'is_abnormalactivity', 'is_foodweight', 'is_cleanness', 'is_recycle', 'is_buffet', 'is_cleaners', 'is_sentiment', 'is_water_tank', 'is_sensor_assign', 'is_annotator_ranking', 'is_superuser', 'is_livestream', 'is_annotator', 'company_annotator', 'is_accesspoint', 'is_cleaners_presence',
            'camera_type_annotator', 'sensor_update_permission', 'assigned_tent'
        )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            # Handle ManyToManyField relationships after saving the user
            if self.cleaned_data.get('company_annotator'):
                user.company_annotator.set(
                    self.cleaned_data['company_annotator'])
            if self.cleaned_data.get('camera_type_annotator'):
                user.camera_type_annotator.set(
                    self.cleaned_data['camera_type_annotator'])
            if self.cleaned_data.get('assigned_tent'):
                user.assigned_tent.set(self.cleaned_data['assigned_tent'])
        return user
