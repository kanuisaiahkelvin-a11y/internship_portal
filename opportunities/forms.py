from django import forms
from django.utils import timezone

from .models import Company, InternshipPosting


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = (
            'name', 'industry', 'location', 'website', 'logo_url',
            'description', 'contact_email', 'contact_phone',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class PostingForm(forms.ModelForm):
    class Meta:
        model = InternshipPosting
        fields = (
            'title', 'description', 'responsibilities', 'requirements',
            'skills_required', 'location', 'work_mode', 'duration_weeks',
            'hours_per_week', 'stipend', 'slots', 'application_deadline', 'start_date',
        )
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'responsibilities': forms.Textarea(attrs={'rows': 3}),
            'requirements': forms.Textarea(attrs={'rows': 3}),
            'skills_required': forms.Textarea(attrs={'rows': 2}),
            'application_deadline': forms.DateInput(attrs={'type': 'date'}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_application_deadline(self):
        deadline = self.cleaned_data['application_deadline']
        is_new_draft = self.instance.pk is None or self.instance.status == InternshipPosting.Status.DRAFT
        if deadline < timezone.localdate() and is_new_draft:
            raise forms.ValidationError('The application deadline cannot be in the past.')
        return deadline

    def clean_slots(self):
        slots = self.cleaned_data['slots']
        if slots < 1:
            raise forms.ValidationError('There must be at least one slot.')
        return slots

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        deadline = cleaned.get('application_deadline')
        if start and deadline and start < deadline:
            self.add_error('start_date', 'The start date must be on or after the application deadline.')
        return cleaned


class PostingFilterForm(forms.Form):
    q = forms.CharField(required=False, label='Search')
    work_mode = forms.ChoiceField(
        required=False,
        choices=[('', 'Any work mode')] + list(InternshipPosting.WorkMode.choices),
    )
    company = forms.ModelChoiceField(
        required=False,
        queryset=Company.objects.all(),
        empty_label='All companies',
    )
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ('newest', 'Newest first'),
            ('deadline', 'Deadline soonest'),
            ('stipend', 'Highest stipend'),
        ],
    )
