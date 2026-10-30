from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from accounts.mixins import RoleRequiredMixin, StudentRequiredMixin
from opportunities.models import InternshipPosting
from notifications.models import Notification

from .forms import (
    ApplicationForm,
    ApplicationStatusForm,
    InterviewForm,
    NoteForm,
    OfferForm,
    OfferResponseForm,
)
from .models import Application, ApplicationNote, ApplicationStatusHistory, Interview, Offer
from .services import (
    InvalidTransition,
    extend_offer,
    notify_new_application,
    respond_to_offer,
    schedule_interview,
    transition_application,
)


def get_employer_company(user):
    profile = getattr(user, 'employer_profile', None)
    return profile.company if profile else None


def can_manage_application(user, application):
    if user.is_coordinator:
        return True
    if user.is_employer:
        return get_employer_company(user) == application.posting.company
    return False


def applications_for_user(user):
    queryset = Application.objects.select_related('student', 'posting__company')
    if user.is_coordinator:
        return queryset
    if user.is_employer:
        company = get_employer_company(user)
        return queryset.filter(posting__company=company) if company else queryset.none()
    return queryset.filter(student=user)


class ApplyView(StudentRequiredMixin, View):
    template_name = 'applications/apply.html'

    def get_posting(self, pk):
        return get_object_or_404(
            InternshipPosting,
            pk=pk,
            status=InternshipPosting.Status.PUBLISHED,
        )

    def get(self, request, pk):
        posting = self.get_posting(pk)
        if Application.objects.filter(posting=posting, student=request.user).exists():
            messages.info(request, 'You have already applied for this internship.')
            return redirect('opportunities:posting_detail', pk=posting.pk)
        return render(
            request,
            self.template_name,
            {'posting': posting, 'form': ApplicationForm()},
        )

    def post(self, request, pk):
        posting = self.get_posting(pk)
        if not posting.is_open:
            messages.error(request, 'This internship is no longer accepting applications.')
            return redirect('opportunities:posting_detail', pk=posting.pk)
        if Application.objects.filter(posting=posting, student=request.user).exists():
            messages.info(request, 'You have already applied for this internship.')
            return redirect('opportunities:posting_detail', pk=posting.pk)

        form = ApplicationForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {'posting': posting, 'form': form},
            )

        profile = getattr(request.user, 'student_profile', None)
        resume = form.cleaned_data.get('resume')
        if not resume and profile and profile.resume:
            resume = profile.resume
        if not resume:
            form.add_error(
                'resume',
                'Upload a resume, or add one to your profile before applying.',
            )
            return render(
                request,
                self.template_name,
                {'posting': posting, 'form': form},
            )

        application = Application.objects.create(
            posting=posting,
            student=request.user,
            cover_letter=form.cleaned_data['cover_letter'],
            resume=resume,
            status=Application.Status.SUBMITTED,
        )
        ApplicationStatusHistory.objects.create(
            application=application,
            from_status='',
            to_status=Application.Status.SUBMITTED,
            changed_by=request.user,
            note='Application submitted.',
        )
        notify_new_application(application)
        messages.success(request, f'Your application for {posting.title} was submitted.')
        return redirect('applications:detail', pk=application.pk)


class MyApplicationsView(StudentRequiredMixin, ListView):
    model = Application
    template_name = 'applications/my_applications.html'
    context_object_name = 'applications'
    paginate_by = 12

    def get_queryset(self):
        queryset = Application.objects.filter(student=self.request.user).select_related(
            'posting__company'
        )
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base = Application.objects.filter(student=self.request.user)
        counts = {
            value: base.filter(status=value).count()
            for value, _label in Application.Status.choices
        }
        context['statuses'] = Application.Status.choices
        context['current_status'] = self.request.GET.get('status', '')
        context['counts'] = counts
        context['total_count'] = base.count()
        context['status_tabs'] = [
            {'value': value, 'label': label, 'count': counts[value]}
            for value, label in Application.Status.choices
        ]
        return context


class ApplicationDetailView(LoginRequiredMixin, DetailView):
    model = Application
    template_name = 'applications/application_detail.html'
    context_object_name = 'application'

    def get_queryset(self):
        return applications_for_user(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.object
        user = self.request.user
        can_manage = can_manage_application(user, application)
        is_owner = application.student_id == user.pk

        context['can_manage'] = can_manage
        context['is_owner'] = is_owner
        context['history'] = application.status_history.select_related('changed_by')
        context['interviews'] = application.interviews.select_related('created_by')
        context['offer'] = getattr(application, 'offer', None)
        context['next_statuses'] = application.allowed_next_statuses

        notes = application.notes.select_related('author')
        if not can_manage:
            notes = notes.filter(is_internal=False)
        context['notes'] = notes
        context['note_form'] = NoteForm()
        if can_manage:
            context['status_form'] = ApplicationStatusForm(application=application)
        return context


class ReviewApplicationsView(RoleRequiredMixin, ListView):
    allowed_roles = ('employer', 'coordinator')
    model = Application
    template_name = 'applications/review_list.html'
    context_object_name = 'applications'
    paginate_by = 20

    def get_queryset(self):
        queryset = applications_for_user(self.request.user)
        status = self.request.GET.get('status')
        posting = self.request.GET.get('posting')
        search = self.request.GET.get('q', '').strip()
        if status:
            queryset = queryset.filter(status=status)
        if posting:
            queryset = queryset.filter(posting_id=posting)
        if search:
            queryset = queryset.filter(
                Q(student__first_name__icontains=search)
                | Q(student__last_name__icontains=search)
                | Q(student__email__icontains=search)
                | Q(posting__title__icontains=search)
            )
        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base = applications_for_user(self.request.user)
        counts = {
            value: base.filter(status=value).count()
            for value, _label in Application.Status.choices
        }
        context['statuses'] = Application.Status.choices
        context['current_status'] = self.request.GET.get('status', '')
        context['postings'] = (
            InternshipPosting.objects.filter(applications__in=base)
            .distinct()
            .order_by('title')
        )
        context['current_posting'] = self.request.GET.get('posting', '')
        context['search'] = self.request.GET.get('q', '')
        context['counts'] = counts
        context['total_count'] = base.count()
        context['status_tabs'] = [
            {'value': value, 'label': label, 'count': counts[value]}
            for value, label in Application.Status.choices
        ]
        return context


@require_POST
def update_status(request, pk):
    application = get_object_or_404(applications_for_user(request.user), pk=pk)
    if not can_manage_application(request.user, application):
        messages.error(request, 'You cannot update that application.')
        return redirect('applications:detail', pk=pk)

    form = ApplicationStatusForm(request.POST, application=application)
    if form.is_valid():
        try:
            transition_application(
                application,
                form.cleaned_data['new_status'],
                request.user,
                note=form.cleaned_data.get('note', ''),
            )
            messages.success(
                request,
                f'Application moved to {application.get_status_display()}.',
            )
        except InvalidTransition as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, 'Select a valid next status.')
    return redirect('applications:detail', pk=pk)


@require_POST
def add_note(request, pk):
    application = get_object_or_404(applications_for_user(request.user), pk=pk)
    is_owner = application.student_id == request.user.pk
    if not (is_owner or can_manage_application(request.user, application)):
        messages.error(request, 'You cannot comment on that application.')
        return redirect('applications:detail', pk=pk)

    form = NoteForm(request.POST)
    if form.is_valid():
        note = form.save(commit=False)
        note.application = application
        note.author = request.user
        if is_owner:
            note.is_internal = False
        note.save()
        if not is_owner:
            Notification.send(
                recipient=application.student,
                title='New message about your application',
                message=f'A new note was added to your application for {application.posting.title}.',
                url=reverse('applications:detail', kwargs={'pk': application.pk}),
                actor=request.user,
            )
        messages.success(request, 'Note added.')
    else:
        messages.error(request, 'The note cannot be empty.')
    return redirect('applications:detail', pk=pk)


class ScheduleInterviewView(RoleRequiredMixin, View):
    allowed_roles = ('employer', 'coordinator')
    template_name = 'applications/interview_form.html'

    def get_application(self, request, pk):
        application = get_object_or_404(applications_for_user(request.user), pk=pk)
        if not can_manage_application(request.user, application):
            return None
        return application

    def get(self, request, pk):
        application = self.get_application(request, pk)
        if application is None:
            messages.error(request, 'You cannot schedule interviews for that application.')
            return redirect('dashboard:home')
        return render(
            request,
            self.template_name,
            {'application': application, 'form': InterviewForm()},
        )

    def post(self, request, pk):
        application = self.get_application(request, pk)
        if application is None:
            messages.error(request, 'You cannot schedule interviews for that application.')
            return redirect('dashboard:home')
        form = InterviewForm(request.POST)
        if form.is_valid():
            schedule_interview(application, form, request.user)
            messages.success(request, 'Interview scheduled and the student was notified.')
            return redirect('applications:detail', pk=pk)
        return render(
            request,
            self.template_name,
            {'application': application, 'form': form},
        )


class ExtendOfferView(RoleRequiredMixin, View):
    allowed_roles = ('employer', 'coordinator')
    template_name = 'applications/offer_form.html'

    def get_application(self, request, pk):
        application = get_object_or_404(applications_for_user(request.user), pk=pk)
        if not can_manage_application(request.user, application):
            return None
        return application

    def get(self, request, pk):
        application = self.get_application(request, pk)
        if application is None:
            messages.error(request, 'You cannot extend offers for that application.')
            return redirect('dashboard:home')
        offer = getattr(application, 'offer', None)
        initial = {}
        if offer is None:
            initial = {
                'start_date': application.posting.start_date,
                'stipend': application.posting.stipend,
            }
        form = OfferForm(instance=offer, initial=initial)
        return render(
            request,
            self.template_name,
            {'application': application, 'form': form, 'offer': offer},
        )

    def post(self, request, pk):
        application = self.get_application(request, pk)
        if application is None:
            messages.error(request, 'You cannot extend offers for that application.')
            return redirect('dashboard:home')

        offer = getattr(application, 'offer', None)
        if offer is None and application.posting.slots_remaining <= 0:
            messages.error(request, 'All internship slots are already filled.')
            return redirect('applications:detail', pk=pk)

        form = OfferForm(request.POST, instance=offer)
        if form.is_valid():
            extend_offer(application, form, request.user)
            messages.success(request, 'Offer extended and the student was notified.')
            return redirect('applications:detail', pk=pk)
        return render(
            request,
            self.template_name,
            {'application': application, 'form': form, 'offer': offer},
        )


@require_POST
def respond_offer(request, pk):
    application = get_object_or_404(Application, pk=pk, student=request.user)
    form = OfferResponseForm(request.POST)
    if not form.is_valid():
        messages.error(request, 'Choose whether to accept or decline the offer.')
        return redirect('applications:detail', pk=pk)

    accept = form.cleaned_data['decision'] == 'accept'
    try:
        respond_to_offer(application, accept, request.user)
        messages.success(
            request,
            'Congratulations! You accepted the offer.' if accept else 'You declined the offer.',
        )
    except InvalidTransition as exc:
        messages.error(request, str(exc))
    return redirect('applications:detail', pk=pk)


@require_POST
def withdraw_application(request, pk):
    application = get_object_or_404(Application, pk=pk, student=request.user)
    if not application.can_withdraw:
        messages.error(request, 'This application can no longer be withdrawn.')
        return redirect('applications:detail', pk=pk)
    try:
        transition_application(
            application,
            Application.Status.WITHDRAWN,
            request.user,
            note='Application withdrawn by student.',
        )
        messages.info(request, 'Your application was withdrawn.')
    except InvalidTransition as exc:
        messages.error(request, str(exc))
    return redirect('applications:detail', pk=pk)
