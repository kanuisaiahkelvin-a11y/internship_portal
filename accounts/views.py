import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import LoginView, LogoutView
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from notifications.models import Notification

from .forms import (
    CoordinatorRequestForm,
    EmailAuthenticationForm,
    EmployerProfileForm,
    RegistrationForm,
    StudentProfileForm,
    UserAccountForm,
)
from .models import CoordinatorRequest, EmployerProfile, StudentProfile, User


class RegisterView(CreateView):
    model = User
    form_class = RegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('dashboard:home')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(
            self.request,
            'Welcome to InternLink! Complete your profile to get started.',
        )
        return response

    # A cached sign-up page would carry an old CSRF token, which fails with
    # "CSRF token incorrect" — common inside installed apps.
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)


class PortalLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm
    redirect_authenticated_user = True


class PortalLogoutView(LogoutView):
    next_page = reverse_lazy('dashboard:home')


@login_required
def profile(request):
    user = request.user
    context = {
        'student_profile': getattr(user, 'student_profile', None),
        'employer_profile': getattr(user, 'employer_profile', None),
    }
    if user.is_student:
        context['applications'] = user.applications.select_related('posting__company')[:5]
        context['bookmarks'] = user.bookmarks.select_related('posting__company')[:5]
    elif user.is_employer:
        profile_obj = getattr(user, 'employer_profile', None)
        company = profile_obj.company if profile_obj else None
        context['company'] = company
        if company:
            context['postings'] = company.postings.all()[:5]
            context['applications'] = (
                company.applications.select_related('student', 'posting')[:5]
                if hasattr(company, 'applications')
                else None
            )
    return render(request, 'accounts/profile.html', context)


@login_required
def profile_edit(request):
    user = request.user
    if user.is_student:
        instance, _ = StudentProfile.objects.get_or_create(user=user)
        profile_form_class = StudentProfileForm
    elif user.is_employer:
        instance, _ = EmployerProfile.objects.get_or_create(user=user)
        profile_form_class = EmployerProfileForm
    else:
        instance = None
        profile_form_class = None

    if request.method == 'POST':
        account_form = UserAccountForm(request.POST, instance=user)
        profile_form = (
            profile_form_class(request.POST, request.FILES, instance=instance)
            if profile_form_class
            else None
        )
        if account_form.is_valid() and (profile_form is None or profile_form.is_valid()):
            account_form.save()
            if profile_form:
                profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('accounts:profile')
    else:
        account_form = UserAccountForm(instance=user)
        profile_form = (
            profile_form_class(instance=instance) if profile_form_class else None
        )

    return render(
        request,
        'accounts/profile_edit.html',
        {'account_form': account_form, 'profile_form': profile_form},
    )


@login_required
def profile_detail(request, pk):
    person = get_object_or_404(User, pk=pk)
    if not (request.user.is_coordinator or request.user.pk == person.pk):
        messages.error(request, 'You can only view your own profile.')
        return redirect('accounts:profile')
    return render(
        request,
        'accounts/profile.html',
        {
            'person': person,
            'student_profile': getattr(person, 'student_profile', None),
            'employer_profile': getattr(person, 'employer_profile', None),
        },
    )


def coordinator_request(request):
    """Public form for a university or internship office to request access."""
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    form = CoordinatorRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        access_request = form.save()
        for coordinator in User.objects.filter(role=User.Role.COORDINATOR):
            Notification.send(
                recipient=coordinator,
                title='New coordinator access request',
                message=(
                    f'{access_request.full_name} from {access_request.institution} '
                    f'requested coordinator access.'
                ),
                url=reverse('dashboard:home'),
            )
        messages.success(
            request,
            'Request sent. The internship office will review it and send your '
            'invite link by email.',
        )
        return redirect(f"{reverse('accounts:coordinator_request')}?sent=1")

    return render(
        request,
        'accounts/coordinator_request.html',
        {'form': form, 'sent': request.GET.get('sent') == '1'},
    )


@login_required
@require_POST
def coordinator_request_approve(request, pk):
    if not request.user.is_coordinator:
        messages.error(request, 'Only coordinators can approve access requests.')
        return redirect('dashboard:home')

    access_request = get_object_or_404(CoordinatorRequest, pk=pk)
    if not access_request.is_pending:
        messages.info(request, 'That request has already been reviewed.')
        return redirect('dashboard:home')

    if User.objects.filter(email__iexact=access_request.email).exists():
        messages.error(
            request,
            f'An account already exists for {access_request.email}. '
            'Nothing was created.',
        )
        return redirect('dashboard:home')

    first_name, _, last_name = access_request.full_name.strip().partition(' ')
    user = User.objects.create_user(
        email=access_request.email,
        password=None,  # unusable until the invite link is used
        first_name=first_name[:150],
        last_name=(last_name or first_name)[:150],
        role=User.Role.COORDINATOR,
    )

    access_request.status = CoordinatorRequest.Status.APPROVED
    access_request.user = user
    access_request.invite_token = uuid.uuid4()
    access_request.reviewed_by = request.user
    access_request.reviewed_at = timezone.now()
    access_request.save(
        update_fields=[
            'status', 'user', 'invite_token', 'reviewed_by', 'reviewed_at',
        ]
    )

    invite_url = request.build_absolute_uri(
        reverse('accounts:coordinator_invite', kwargs={'token': access_request.invite_token})
    )
    send_mail(
        subject='Your InternLink coordinator account',
        message=(
            f'Hello {access_request.full_name},\n\n'
            f'Your coordinator access for {access_request.institution} was approved.\n'
            f'Set your password here:\n\n{invite_url}\n\n'
            'This link works once. If it expires, ask the internship office for a new one.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )

    messages.success(
        request,
        f'Access approved for {user.email}. Send them this invite link: {invite_url}',
    )
    return redirect('dashboard:home')


@login_required
@require_POST
def coordinator_request_reject(request, pk):
    if not request.user.is_coordinator:
        messages.error(request, 'Only coordinators can review access requests.')
        return redirect('dashboard:home')

    access_request = get_object_or_404(CoordinatorRequest, pk=pk)
    if not access_request.is_pending:
        messages.info(request, 'That request has already been reviewed.')
        return redirect('dashboard:home')

    access_request.status = CoordinatorRequest.Status.REJECTED
    access_request.reviewed_by = request.user
    access_request.reviewed_at = timezone.now()
    access_request.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
    messages.success(request, f'Request from {access_request.full_name} rejected.')
    return redirect('dashboard:home')


def coordinator_invite(request, token):
    """One-time link where an approved coordinator sets a password."""
    access_request = get_object_or_404(
        CoordinatorRequest,
        invite_token=token,
        status=CoordinatorRequest.Status.APPROVED,
        user__isnull=False,
    )
    user = access_request.user

    form = SetPasswordForm(user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        access_request.invite_token = None
        access_request.save(update_fields=['invite_token'])
        login(
            request,
            user,
            backend='django.contrib.auth.backends.ModelBackend',
        )
        messages.success(
            request,
            'Your coordinator account is ready. Welcome to InternLink!',
        )
        return redirect('dashboard:home')

    return render(
        request,
        'accounts/coordinator_invite.html',
        {'form': form, 'access_request': access_request},
    )
