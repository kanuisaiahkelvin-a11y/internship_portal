import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone


def application_resume_path(instance, filename):
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'pdf'
    return f'resumes/applications/{uuid.uuid4().hex}.{extension}'


class Application(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'under_review', 'Under Review'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        INTERVIEW = 'interview', 'Interview'
        OFFERED = 'offered', 'Offer Extended'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    # Allowed forward moves for the review pipeline.
    TRANSITIONS = {
        Status.SUBMITTED: [Status.UNDER_REVIEW, Status.REJECTED, Status.WITHDRAWN],
        Status.UNDER_REVIEW: [Status.SHORTLISTED, Status.REJECTED, Status.WITHDRAWN],
        Status.SHORTLISTED: [Status.INTERVIEW, Status.OFFERED, Status.REJECTED, Status.WITHDRAWN],
        Status.INTERVIEW: [Status.OFFERED, Status.REJECTED, Status.WITHDRAWN],
        Status.OFFERED: [Status.ACCEPTED, Status.REJECTED, Status.WITHDRAWN],
        Status.ACCEPTED: [],
        Status.REJECTED: [],
        Status.WITHDRAWN: [],
    }

    STATUS_COLORS = {
        Status.SUBMITTED: 'secondary',
        Status.UNDER_REVIEW: 'info',
        Status.SHORTLISTED: 'primary',
        Status.INTERVIEW: 'warning',
        Status.OFFERED: 'success',
        Status.ACCEPTED: 'success',
        Status.REJECTED: 'danger',
        Status.WITHDRAWN: 'dark',
    }

    posting = models.ForeignKey(
        'opportunities.InternshipPosting',
        on_delete=models.CASCADE,
        related_name='applications',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications',
    )
    cover_letter = models.TextField(blank=True)
    resume = models.FileField(upload_to=application_resume_path)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['posting', 'student'], name='unique_application_per_posting'),
        ]

    def __str__(self):
        return f'{self.student.full_name} → {self.posting.title}'

    def get_absolute_url(self):
        return reverse('applications:detail', kwargs={'pk': self.pk})

    @property
    def status_color(self):
        return self.STATUS_COLORS.get(self.status, 'secondary')

    @property
    def can_withdraw(self):
        return self.status not in (
            self.Status.ACCEPTED,
            self.Status.REJECTED,
            self.Status.WITHDRAWN,
        )

    @property
    def allowed_next_statuses(self):
        return self.TRANSITIONS.get(self.status, [])

    def can_transition_to(self, new_status):
        return new_status in self.allowed_next_statuses

    def clean(self):
        if self.posting_id and self.student_id and self.student.role != 'student':
            raise ValidationError('Only students can submit applications.')


class ApplicationStatusHistory(models.Model):
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='status_history',
    )
    from_status = models.CharField(max_length=20, choices=Application.Status.choices, blank=True)
    to_status = models.CharField(max_length=20, choices=Application.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='application_status_changes',
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name_plural = 'Application status history'

    def __str__(self):
        return f'{self.application_id}: {self.from_status or "new"} → {self.to_status}'


class ApplicationNote(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    is_internal = models.BooleanField(
        default=True,
        help_text='Internal notes are only visible to employers and coordinators.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Note by {self.author.full_name} on {self.application_id}'


class Interview(models.Model):
    class Mode(models.TextChoices):
        ONSITE = 'onsite', 'On-site'
        ONLINE = 'online', 'Online'
        PHONE = 'phone', 'Phone'

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'

    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    scheduled_at = models.DateTimeField()
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.ONLINE)
    location = models.CharField(max_length=255, blank=True, help_text='Address or meeting link.')
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='scheduled_interviews',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_at']

    def __str__(self):
        return f'Interview for {self.application} on {self.scheduled_at:%Y-%m-%d %H:%M}'

    @property
    def is_upcoming(self):
        return self.status == self.Status.SCHEDULED and self.scheduled_at >= timezone.now()


class Offer(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='offer')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    stipend = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    details = models.TextField(blank=True)
    response_deadline = models.DateField(null=True, blank=True)
    offered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='offers_made',
    )
    offered_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-offered_at']

    def __str__(self):
        return f'Offer for {self.application}'

    @property
    def is_pending(self):
        return self.application.status == Application.Status.OFFERED
