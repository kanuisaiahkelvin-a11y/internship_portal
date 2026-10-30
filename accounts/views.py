from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import (
    EmailAuthenticationForm,
    EmployerProfileForm,
    RegistrationForm,
    StudentProfileForm,
    UserAccountForm,
)
from .models import EmployerProfile, StudentProfile, User


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
