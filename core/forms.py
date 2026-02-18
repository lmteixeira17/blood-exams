"""
Forms for the blood exams system.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Exam, UserProfile


class RegistrationForm(UserCreationForm):
    """User registration form with profile fields."""

    email = forms.EmailField(required=True, label='E-mail')
    first_name = forms.CharField(max_length=150, required=True, label='Nome')
    last_name = forms.CharField(max_length=150, required=True, label='Sobrenome')
    date_of_birth = forms.DateField(
        required=False,
        label='Data de Nascimento',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    gender = forms.ChoiceField(
        choices=[('', 'Selecione...')] + UserProfile.GENDER_CHOICES,
        required=False,
        label='Sexo',
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            # Update profile (created by signal)
            user.profile.date_of_birth = self.cleaned_data.get('date_of_birth')
            user.profile.gender = self.cleaned_data.get('gender', '')
            user.profile.save()
        return user


class ProfileForm(forms.ModelForm):
    """User profile edit form."""

    first_name = forms.CharField(max_length=150, required=True, label='Nome')
    last_name = forms.CharField(max_length=150, required=True, label='Sobrenome')
    email = forms.EmailField(required=True, label='E-mail')

    class Meta:
        model = UserProfile
        fields = ['date_of_birth', 'gender']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.user.first_name = self.cleaned_data['first_name']
            profile.user.last_name = self.cleaned_data['last_name']
            profile.user.email = self.cleaned_data['email']
            profile.user.save()
            profile.save()
        return profile


class ExamUploadForm(forms.ModelForm):
    """Exam file upload form."""

    class Meta:
        model = Exam
        fields = ['file', 'exam_date', 'lab_name']
        widgets = {
            'exam_date': forms.DateInput(attrs={'type': 'date'}),
            'lab_name': forms.TextInput(attrs={'placeholder': 'Ex: Laboratório Fleury'}),
        }

    def clean_file(self):
        f = self.cleaned_data.get('file')
        if f:
            ext = f.name.lower().split('.')[-1]
            allowed = ['pdf', 'jpg', 'jpeg', 'png']
            if ext not in allowed:
                raise forms.ValidationError(
                    f'Formato não suportado: .{ext}. Use PDF, JPG ou PNG.'
                )
            if f.size > 20 * 1024 * 1024:
                raise forms.ValidationError('Arquivo muito grande. Máximo: 20MB.')
        return f
