from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import CoordinatorRequest, EmployerProfile, StudentProfile, User


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email address',
        widget=forms.EmailInput(attrs={'autofocus': True, 'class': 'form-control'}),
    )


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    role = forms.ChoiceField(
        choices=[
            (User.Role.STUDENT, 'I am a student looking for an internship'),
            (User.Role.EMPLOYER, 'I represent a company offering internships'),
        ],
        widget=forms.RadioSelect,
        initial=User.Role.STUDENT,
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'role', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = (
            'school', 'course', 'year_level', 'expected_graduation', 'location',
            'skills', 'bio', 'resume', 'linkedin_url', 'portfolio_url',
        )
        widgets = {
            'expected_graduation': forms.DateInput(attrs={'type': 'date'}),
            'bio': forms.Textarea(attrs={'rows': 4}),
            'skills': forms.Textarea(attrs={'rows': 2}),
        }


class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ('company', 'job_title')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = self.fields['company'].queryset.select_related()
        self.fields['company'].empty_label = '— Select your company —'


class UserAccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone')


class CoordinatorRequestForm(forms.ModelForm):
    class Meta:
        model = CoordinatorRequest
        fields = ('full_name', 'institution', 'email', 'message')
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                'An account with this email already exists. Log in instead.'
            )
        if CoordinatorRequest.objects.filter(
            email__iexact=email, status=CoordinatorRequest.Status.PENDING
        ).exists():
            raise forms.ValidationError(
                'A request for this email is already waiting for review.'
            )
        return email
