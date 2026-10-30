from django import forms

from .models import Application, ApplicationNote, Interview, Offer


class ApplicationForm(forms.ModelForm):
    resume = forms.FileField(
        required=False,
        help_text='PDF or Word document. If left blank, the resume on your profile is used.',
    )

    class Meta:
        model = Application
        fields = ('cover_letter', 'resume')
        widgets = {
            'cover_letter': forms.Textarea(
                attrs={
                    'rows': 6,
                    'placeholder': 'Tell the employer why you are a good fit for this internship.',
                }
            ),
        }


class ApplicationStatusForm(forms.Form):
    new_status = forms.ChoiceField(label='Move to')
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2}),
        label='Note (optional)',
    )

    def __init__(self, *args, application=None, **kwargs):
        super().__init__(*args, **kwargs)
        if application is not None:
            choices = [
                (status, dict(Application.Status.choices)[status])
                for status in application.allowed_next_statuses
                if status != Application.Status.WITHDRAWN
            ]
            self.fields['new_status'].choices = choices
            if not choices:
                self.fields['new_status'].disabled = True


class NoteForm(forms.ModelForm):
    class Meta:
        model = ApplicationNote
        fields = ('content', 'is_internal')
        widgets = {'content': forms.Textarea(attrs={'rows': 3})}


class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = ('scheduled_at', 'mode', 'location', 'notes')
        widgets = {
            'scheduled_at': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['scheduled_at'].input_formats = ['%Y-%m-%dT%H:%M']


class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        fields = ('start_date', 'end_date', 'stipend', 'details', 'response_deadline')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'response_deadline': forms.DateInput(attrs={'type': 'date'}),
            'details': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        if start and end and end < start:
            self.add_error('end_date', 'The end date must be after the start date.')
        return cleaned


class OfferResponseForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[('accept', 'Accept offer'), ('decline', 'Decline offer')],
        widget=forms.RadioSelect,
        label='Your decision',
    )
