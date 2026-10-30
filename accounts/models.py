from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.urls import reverse


class UserManager(BaseUserManager):
    """Manager for a user model that logs in with email instead of username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('An email address is required.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.COORDINATOR)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        EMPLOYER = 'employer', 'Employer'
        COORDINATOR = 'coordinator', 'Internship Coordinator'

    username = None
    email = models.EmailField('email address', unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    phone = models.CharField(max_length=30, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return self.full_name or self.email

    def get_absolute_url(self):
        return reverse('accounts:profile')

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_employer(self):
        return self.role == self.Role.EMPLOYER

    @property
    def is_coordinator(self):
        return self.role == self.Role.COORDINATOR or self.is_superuser


class StudentProfile(models.Model):
    class YearLevel(models.TextChoices):
        FIRST = '1', '1st Year'
        SECOND = '2', '2nd Year'
        THIRD = '3', '3rd Year'
        FOURTH = '4', '4th Year'
        FIFTH = '5', '5th Year'
        GRADUATE = 'grad', 'Graduate Student'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    school = models.CharField(max_length=200, blank=True)
    course = models.CharField(max_length=200, blank=True)
    year_level = models.CharField(max_length=10, choices=YearLevel.choices, blank=True)
    expected_graduation = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    skills = models.TextField(
        blank=True,
        help_text='Separate skills with commas, e.g. Python, Data Analysis, Communication.',
    )
    bio = models.TextField(blank=True)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    linkedin_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Student profile: {self.user.full_name}'

    @property
    def skill_list(self):
        return [skill.strip() for skill in self.skills.split(',') if skill.strip()]

    @property
    def is_complete(self):
        return bool(self.school and self.course and self.resume)


class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    company = models.ForeignKey(
        'opportunities.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='representatives',
    )
    job_title = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Employer profile: {self.user.full_name}'


class CoordinatorRequest(models.Model):
    """An access request from a university or internship office.

    Coordinator accounts cannot self-register: the office submits a request and
    an existing coordinator approves it, which creates the account and hands
    back a one-time link for setting a password.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    full_name = models.CharField(max_length=150)
    institution = models.CharField(max_length=200)
    email = models.EmailField()
    message = models.TextField(
        blank=True,
        help_text='Optional: your role at the institution and how you will use the portal.',
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    invite_token = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coordinator_request',
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_coordinator_requests',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'coordinator access request'

    def __str__(self):
        return f'{self.institution} — {self.full_name}'

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def can_use_invite(self):
        return bool(self.invite_token and self.status == self.Status.APPROVED)
