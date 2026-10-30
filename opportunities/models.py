from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Company(models.Model):
    name = models.CharField(max_length=200)
    industry = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=200)
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True, help_text='Optional link to your company logo.')
    description = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_companies',
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_companies',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Companies'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('opportunities:company_detail', kwargs={'pk': self.pk})

    @property
    def active_postings(self):
        return self.postings.filter(status=InternshipPosting.Status.PUBLISHED)

    @property
    def applications(self):
        from applications.models import Application

        return Application.objects.filter(posting__company=self)


class InternshipPosting(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING = 'pending', 'Pending Review'
        PUBLISHED = 'published', 'Published'
        CLOSED = 'closed', 'Closed'

    class WorkMode(models.TextChoices):
        ONSITE = 'onsite', 'On-site'
        REMOTE = 'remote', 'Remote'
        HYBRID = 'hybrid', 'Hybrid'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='postings')
    title = models.CharField(max_length=200)
    description = models.TextField()
    responsibilities = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    skills_required = models.TextField(
        blank=True,
        help_text='Separate skills with commas, e.g. Python, Excel, Customer Service.',
    )
    location = models.CharField(max_length=200)
    work_mode = models.CharField(max_length=20, choices=WorkMode.choices, default=WorkMode.ONSITE)
    duration_weeks = models.PositiveIntegerField(default=8)
    hours_per_week = models.PositiveIntegerField(default=20)
    stipend = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Monthly stipend in your local currency. Enter 0 if unpaid.',
    )
    slots = models.PositiveIntegerField(default=1)
    application_deadline = models.DateField()
    start_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    is_featured = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='postings',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_postings',
    )
    review_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_featured', '-created_at']
        indexes = [
            models.Index(fields=['status', 'application_deadline']),
            models.Index(fields=['work_mode']),
        ]

    def __str__(self):
        return f'{self.title} at {self.company.name}'

    def get_absolute_url(self):
        return reverse('opportunities:posting_detail', kwargs={'pk': self.pk})

    @property
    def skill_list(self):
        return [skill.strip() for skill in self.skills_required.split(',') if skill.strip()]

    @property
    def is_open(self):
        if self.status != self.Status.PUBLISHED:
            return False
        if self.application_deadline < timezone.localdate():
            return False
        return self.slots_remaining > 0

    @property
    def accepted_count(self):
        return self.applications.filter(status='accepted').count()

    @property
    def slots_remaining(self):
        return max(self.slots - self.accepted_count, 0)

    @property
    def application_count(self):
        return self.applications.count()

    @property
    def is_deadline_soon(self):
        if self.status != self.Status.PUBLISHED:
            return False
        days = (self.application_deadline - timezone.localdate()).days
        return 0 <= days <= 7

    def publish(self, reviewer):
        self.status = self.Status.PUBLISHED
        self.reviewed_by = reviewer
        self.review_notes = ''
        self.save(update_fields=['status', 'reviewed_by', 'review_notes', 'updated_at'])


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookmarks',
    )
    posting = models.ForeignKey(InternshipPosting, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'posting'], name='unique_bookmark_per_user'),
        ]

    def __str__(self):
        return f'{self.user} saved {self.posting}'
