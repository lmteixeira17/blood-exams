"""
Forms for the blood exams system.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Exam, Medication, UserMedication, UserProfile


# Use dd/mm/YYYY text inputs instead of HTML5 type="date" (which uses browser locale).
DATE_INPUT_FORMATS = ['%d/%m/%Y', '%Y-%m-%d']
DATE_WIDGET = forms.TextInput(attrs={'placeholder': 'dd/mm/aaaa', 'maxlength': '10', 'class': 'date-input'})


class RegistrationForm(UserCreationForm):
    """User registration form with profile fields."""

    email = forms.EmailField(required=True, label='E-mail')
    first_name = forms.CharField(max_length=150, required=True, label='Nome')
    last_name = forms.CharField(max_length=150, required=True, label='Sobrenome')
    date_of_birth = forms.DateField(
        required=False,
        label='Data de Nascimento',
        input_formats=DATE_INPUT_FORMATS,
        widget=forms.TextInput(attrs={'placeholder': 'dd/mm/aaaa', 'maxlength': '10', 'class': 'date-input'}),
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
    """User profile edit form with password change support."""

    first_name = forms.CharField(max_length=150, required=True, label='Nome')
    last_name = forms.CharField(max_length=150, required=True, label='Sobrenome')
    email = forms.EmailField(required=True, label='E-mail')

    # Password change (all optional - only validated when any is filled)
    current_password = forms.CharField(
        required=False, label='Senha Atual',
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
    )
    new_password = forms.CharField(
        required=False, label='Nova Senha',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        min_length=8,
    )
    confirm_password = forms.CharField(
        required=False, label='Confirmar Nova Senha',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = UserProfile
        fields = ['date_of_birth', 'gender']
        widgets = {
            'date_of_birth': forms.TextInput(attrs={'placeholder': 'dd/mm/aaaa', 'maxlength': '10', 'class': 'date-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date_of_birth'].input_formats = DATE_INPUT_FORMATS
        # Render existing date as dd/mm/yyyy
        if self.instance and self.instance.date_of_birth:
            self.initial['date_of_birth'] = self.instance.date_of_birth.strftime('%d/%m/%Y')
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def clean(self):
        cleaned = super().clean()
        current = cleaned.get('current_password', '')
        new = cleaned.get('new_password', '')
        confirm = cleaned.get('confirm_password', '')

        # If any password field is filled, all are required
        if current or new or confirm:
            if not current:
                self.add_error('current_password', 'Informe a senha atual.')
            elif not self.instance.user.check_password(current):
                self.add_error('current_password', 'Senha atual incorreta.')
            if not new:
                self.add_error('new_password', 'Informe a nova senha.')
            if not confirm:
                self.add_error('confirm_password', 'Confirme a nova senha.')
            elif new and confirm and new != confirm:
                self.add_error('confirm_password', 'As senhas não coincidem.')

        return cleaned

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.user.first_name = self.cleaned_data['first_name']
            profile.user.last_name = self.cleaned_data['last_name']
            profile.user.email = self.cleaned_data['email']

            # Change password if provided
            new_password = self.cleaned_data.get('new_password')
            if new_password:
                profile.user.set_password(new_password)

            profile.user.save()
            profile.save()
        return profile


class AdminUserForm(forms.Form):
    """Admin form for creating/editing users."""

    username = forms.CharField(max_length=150, label='Usuário')
    first_name = forms.CharField(max_length=150, required=False, label='Nome')
    last_name = forms.CharField(max_length=150, required=False, label='Sobrenome')
    email = forms.EmailField(required=False, label='E-mail')
    date_of_birth = forms.DateField(
        required=False, label='Data de Nascimento',
        input_formats=DATE_INPUT_FORMATS,
        widget=forms.TextInput(attrs={'placeholder': 'dd/mm/aaaa', 'maxlength': '10', 'class': 'date-input'}),
    )
    gender = forms.ChoiceField(
        choices=[('', 'Selecione...')] + UserProfile.GENDER_CHOICES,
        required=False, label='Sexo',
    )
    is_superuser = forms.BooleanField(required=False, label='Administrador')
    is_active = forms.BooleanField(required=False, initial=True, label='Ativo')
    password = forms.CharField(
        required=False, label='Senha',
        widget=forms.PasswordInput,
        min_length=8,
        help_text='Mínimo 8 caracteres. Deixe em branco para não alterar (edição).',
    )

    def __init__(self, *args, **kwargs):
        self.editing_user = kwargs.pop('editing_user', None)
        super().__init__(*args, **kwargs)
        if self.editing_user:
            self.fields['username'].initial = self.editing_user.username
            self.fields['first_name'].initial = self.editing_user.first_name
            self.fields['last_name'].initial = self.editing_user.last_name
            self.fields['email'].initial = self.editing_user.email
            self.fields['is_superuser'].initial = self.editing_user.is_superuser
            self.fields['is_active'].initial = self.editing_user.is_active
            if hasattr(self.editing_user, 'profile'):
                self.fields['gender'].initial = self.editing_user.profile.gender
                if self.editing_user.profile.date_of_birth:
                    self.fields['date_of_birth'].initial = self.editing_user.profile.date_of_birth.strftime('%d/%m/%Y')
        else:
            # Password required for new users
            self.fields['password'].required = True

    def clean_username(self):
        username = self.cleaned_data['username']
        qs = User.objects.filter(username=username)
        if self.editing_user:
            qs = qs.exclude(pk=self.editing_user.pk)
        if qs.exists():
            raise forms.ValidationError('Este nome de usuário já está em uso.')
        return username

    def save(self):
        data = self.cleaned_data
        if self.editing_user:
            user = self.editing_user
            user.username = data['username']
            user.first_name = data['first_name']
            user.last_name = data['last_name']
            user.email = data['email']
            user.is_superuser = data['is_superuser']
            user.is_staff = data['is_superuser']
            user.is_active = data['is_active']
            if data['password']:
                user.set_password(data['password'])
            user.save()
        else:
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                first_name=data['first_name'],
                last_name=data['last_name'],
            )
            user.is_superuser = data['is_superuser']
            user.is_staff = data['is_superuser']
            user.is_active = data['is_active']
            user.save()

        # Update profile
        profile = user.profile
        profile.date_of_birth = data['date_of_birth']
        profile.gender = data['gender']
        profile.save()

        return user


class CompleteProfileForm(forms.Form):
    """Form to collect required profile data (DOB and gender) on first login."""

    date_of_birth = forms.DateField(
        required=True, label='Data de Nascimento',
        input_formats=DATE_INPUT_FORMATS,
        widget=forms.TextInput(attrs={'placeholder': 'dd/mm/aaaa', 'maxlength': '10', 'class': 'date-input'}),
    )
    gender = forms.ChoiceField(
        choices=UserProfile.GENDER_CHOICES,
        required=True, label='Sexo',
    )


class ExamUploadForm(forms.ModelForm):
    """Exam file upload form."""

    class Meta:
        model = Exam
        fields = ['file', 'exam_date', 'lab_name']
        widgets = {
            'exam_date': forms.TextInput(attrs={'placeholder': 'dd/mm/aaaa', 'maxlength': '10', 'class': 'date-input'}),
            'lab_name': forms.TextInput(attrs={'placeholder': 'Ex: Laboratório Fleury'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['exam_date'].input_formats = DATE_INPUT_FORMATS

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


class UserMedicationForm(forms.ModelForm):
    """Form for adding/editing a user medication."""

    medication_name = forms.CharField(
        max_length=200, required=False, label='Novo Medicamento',
        widget=forms.TextInput(attrs={'placeholder': 'Digite se não encontrar na lista'}),
        help_text='Use apenas se o medicamento não estiver na lista acima',
    )
    medication_type = forms.ChoiceField(
        choices=Medication.TYPE_CHOICES,
        required=False, label='Tipo do Novo Medicamento',
    )

    class Meta:
        model = UserMedication
        fields = ['medication', 'dose', 'frequency', 'start_date', 'end_date', 'notes']
        widgets = {
            'medication': forms.Select(attrs={'class': 'medication-select'}),
            'dose': forms.TextInput(attrs={'placeholder': 'Ex: 1000 UI, 50 mcg'}),
            'start_date': forms.TextInput(attrs={'placeholder': 'dd/mm/aaaa', 'maxlength': '10', 'class': 'date-input'}),
            'end_date': forms.TextInput(attrs={'placeholder': 'dd/mm/aaaa', 'maxlength': '10', 'class': 'date-input'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ex: tomar em jejum, com refeição...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['medication'].queryset = Medication.objects.order_by('name')
        self.fields['medication'].required = False
        self.fields['medication'].empty_label = 'Selecione um medicamento...'
        self.fields['start_date'].input_formats = DATE_INPUT_FORMATS
        self.fields['end_date'].input_formats = DATE_INPUT_FORMATS
        self.fields['end_date'].required = False
        # Format existing dates as dd/mm/yyyy
        if self.instance and self.instance.pk:
            if self.instance.start_date:
                self.initial['start_date'] = self.instance.start_date.strftime('%d/%m/%Y')
            if self.instance.end_date:
                self.initial['end_date'] = self.instance.end_date.strftime('%d/%m/%Y')

    def clean(self):
        cleaned = super().clean()
        medication = cleaned.get('medication')
        medication_name = cleaned.get('medication_name', '').strip()

        if not medication and not medication_name:
            raise forms.ValidationError('Selecione um medicamento da lista ou digite um novo nome.')

        if medication_name and not medication:
            # Create new medication
            med_type = cleaned.get('medication_type', 'medication')
            med, created = Medication.objects.get_or_create(
                name=medication_name,
                defaults={'type': med_type},
            )
            cleaned['medication'] = med

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.medication = self.cleaned_data['medication']
        if commit:
            instance.save()
        return instance
