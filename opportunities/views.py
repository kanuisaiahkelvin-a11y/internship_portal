from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.mixins import CoordinatorRequiredMixin, EmployerRequiredMixin, StudentRequiredMixin
from applications.models import Application
from notifications.models import Notification

from .forms import CompanyForm, PostingFilterForm, PostingForm
from .models import Bookmark, Company, InternshipPosting

User = get_user_model()


def get_employer_company(user):
    profile = getattr(user, 'employer_profile', None)
    return profile.company if profile else None


def is_company_representative(user, company):
    if not user.is_authenticated:
        return False
    return user.is_coordinator or get_employer_company(user) == company


class PostingListView(ListView):
    model = InternshipPosting
    template_name = 'opportunities/posting_list.html'
    context_object_name = 'postings'
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            InternshipPosting.objects.filter(status=InternshipPosting.Status.PUBLISHED)
            .select_related('company')
        )

        search = self.request.GET.get('q', '').strip()
        work_mode = self.request.GET.get('work_mode', '').strip()
        company_id = self.request.GET.get('company', '').strip()
        sort = self.request.GET.get('sort', 'newest')

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(skills_required__icontains=search)
                | Q(company__name__icontains=search)
                | Q(location__icontains=search)
            )
        if work_mode:
            queryset = queryset.filter(work_mode=work_mode)
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        if sort == 'deadline':
            queryset = queryset.order_by('application_deadline', '-is_featured')
        elif sort == 'stipend':
            queryset = queryset.order_by('-stipend', '-is_featured')
        else:
            queryset = queryset.order_by('-is_featured', '-created_at')
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = PostingFilterForm(self.request.GET or None)
        context['companies'] = Company.objects.filter(
            postings__status=InternshipPosting.Status.PUBLISHED
        ).distinct()
        context['total_count'] = self.get_queryset().count()
        context['saved_ids'] = set()
        if self.request.user.is_authenticated:
            context['saved_ids'] = set(
                self.request.user.bookmarks.values_list('posting_id', flat=True)
            )
        return context


class PostingDetailView(DetailView):
    model = InternshipPosting
    template_name = 'opportunities/posting_detail.html'
    context_object_name = 'posting'

    def get_queryset(self):
        queryset = InternshipPosting.objects.select_related('company')
        user = self.request.user
        if user.is_authenticated and user.is_coordinator:
            return queryset
        if user.is_authenticated and user.is_employer:
            company = get_employer_company(user)
            if company:
                return queryset.filter(
                    Q(status=InternshipPosting.Status.PUBLISHED) | Q(company=company)
                )
        return queryset.filter(status=InternshipPosting.Status.PUBLISHED)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        posting = self.object
        user = self.request.user
        is_owner = is_company_representative(user, posting.company)

        context['is_owner'] = is_owner
        context['can_apply'] = False
        context['application'] = None
        context['is_bookmarked'] = False
        context['similar_postings'] = (
            InternshipPosting.objects.filter(
                company=posting.company,
                status=InternshipPosting.Status.PUBLISHED,
            )
            .exclude(pk=posting.pk)[:3]
        )

        if user.is_authenticated and user.is_student:
            application = Application.objects.filter(posting=posting, student=user).first()
            context['application'] = application
            context['is_bookmarked'] = Bookmark.objects.filter(user=user, posting=posting).exists()
            context['can_apply'] = posting.is_open and application is None

        if is_owner:
            context['applications'] = (
                posting.applications.select_related('student')
                .order_by('-created_at')[:10]
            )
            context['application_count'] = posting.application_count
        return context


class PostingCreateView(EmployerRequiredMixin, CreateView):
    model = InternshipPosting
    form_class = PostingForm
    template_name = 'opportunities/posting_form.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.company = get_employer_company(request.user)
            if not self.company:
                messages.error(
                    request,
                    'Create or link a company profile before posting an internship.',
                )
                return redirect('opportunities:company_create')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.company = self.company
        form.instance.created_by = self.request.user
        form.instance.status = InternshipPosting.Status.DRAFT
        response = super().form_valid(form)
        messages.success(
            self.request,
            'Draft saved. Submit it for coordinator review when you are ready to publish.',
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Post a new internship'
        return context


class PostingUpdateView(EmployerRequiredMixin, UpdateView):
    model = InternshipPosting
    form_class = PostingForm
    template_name = 'opportunities/posting_form.html'

    def get_queryset(self):
        queryset = InternshipPosting.objects.select_related('company')
        if self.request.user.is_coordinator:
            return queryset
        company = get_employer_company(self.request.user)
        return queryset.filter(company=company) if company else queryset.none()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Internship posting updated.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Edit internship posting'
        return context


class PostingDeleteView(EmployerRequiredMixin, DeleteView):
    model = InternshipPosting
    template_name = 'opportunities/posting_confirm_delete.html'
    success_url = reverse_lazy('opportunities:my_postings')

    def get_queryset(self):
        queryset = InternshipPosting.objects.select_related('company')
        if self.request.user.is_coordinator:
            return queryset
        company = get_employer_company(self.request.user)
        return queryset.filter(company=company) if company else queryset.none()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        posting = self.get_object()
        if posting.status not in (
            InternshipPosting.Status.DRAFT,
            InternshipPosting.Status.CLOSED,
        ) and not request.user.is_coordinator:
            messages.error(request, 'Only draft or closed postings can be deleted.')
            return redirect('opportunities:posting_detail', pk=posting.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Internship posting deleted.')
        return super().form_valid(form)


@require_POST
def submit_posting(request, pk):
    posting = get_object_or_404(InternshipPosting, pk=pk)
    if not is_company_representative(request.user, posting.company):
        messages.error(request, 'You cannot submit that posting.')
        return redirect('opportunities:posting_detail', pk=pk)
    if posting.status != InternshipPosting.Status.DRAFT:
        messages.error(request, 'Only draft postings can be submitted for review.')
        return redirect('opportunities:posting_detail', pk=pk)

    posting.status = InternshipPosting.Status.PENDING
    posting.save(update_fields=['status', 'updated_at'])
    for coordinator in User.objects.filter(role=User.Role.COORDINATOR, is_active=True):
        Notification.send(
            recipient=coordinator,
            title='Posting awaiting review',
            message=f'{posting.company.name} submitted "{posting.title}" for review.',
            url=reverse('opportunities:posting_detail', kwargs={'pk': posting.pk}),
            actor=request.user,
        )
    messages.success(request, 'Posting submitted for coordinator review.')
    return redirect('opportunities:posting_detail', pk=pk)


@require_POST
def close_posting(request, pk):
    posting = get_object_or_404(InternshipPosting, pk=pk)
    if not is_company_representative(request.user, posting.company):
        messages.error(request, 'You cannot close that posting.')
        return redirect('opportunities:posting_detail', pk=pk)
    if posting.status not in (
        InternshipPosting.Status.PUBLISHED,
        InternshipPosting.Status.PENDING,
    ):
        messages.error(request, 'That posting cannot be closed right now.')
        return redirect('opportunities:posting_detail', pk=pk)

    posting.status = InternshipPosting.Status.CLOSED
    posting.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Posting closed. It is no longer accepting applications.')
    return redirect('opportunities:posting_detail', pk=pk)


@require_POST
def approve_posting(request, pk):
    if not request.user.is_coordinator:
        messages.error(request, 'Only coordinators can approve postings.')
        return redirect('opportunities:posting_detail', pk=pk)

    posting = get_object_or_404(InternshipPosting, pk=pk)
    if posting.status != InternshipPosting.Status.PENDING:
        messages.error(request, 'Only postings pending review can be approved.')
        return redirect('opportunities:posting_detail', pk=pk)

    posting.publish(request.user)
    Notification.send(
        recipient=posting.created_by,
        title='Posting approved',
        message=f'"{posting.title}" is now live on InternLink.',
        url=reverse('opportunities:posting_detail', kwargs={'pk': posting.pk}),
        actor=request.user,
    )
    messages.success(request, 'Posting approved and published.')
    return redirect('opportunities:review_postings')


@require_POST
def reject_posting(request, pk):
    if not request.user.is_coordinator:
        messages.error(request, 'Only coordinators can reject postings.')
        return redirect('opportunities:posting_detail', pk=pk)

    posting = get_object_or_404(InternshipPosting, pk=pk)
    if posting.status != InternshipPosting.Status.PENDING:
        messages.error(request, 'Only postings pending review can be returned.')
        return redirect('opportunities:posting_detail', pk=pk)

    posting.status = InternshipPosting.Status.DRAFT
    posting.reviewed_by = request.user
    posting.review_notes = request.POST.get('review_notes', '').strip()
    posting.save(update_fields=['status', 'reviewed_by', 'review_notes', 'updated_at'])
    Notification.send(
        recipient=posting.created_by,
        title='Posting needs changes',
        message=(
            f'"{posting.title}" was returned for revision.'
            + (f' Notes: {posting.review_notes}' if posting.review_notes else '')
        ),
        url=reverse('opportunities:posting_detail', kwargs={'pk': posting.pk}),
        actor=request.user,
    )
    messages.success(request, 'Posting returned to the employer for revision.')
    return redirect('opportunities:review_postings')


class MyPostingsView(EmployerRequiredMixin, ListView):
    model = InternshipPosting
    template_name = 'opportunities/my_postings.html'
    context_object_name = 'postings'

    def get_queryset(self):
        company = get_employer_company(self.request.user)
        if not company:
            return InternshipPosting.objects.none()
        queryset = company.postings.select_related('company')
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = get_employer_company(self.request.user)
        context['company'] = company
        if company:
            all_postings = company.postings.all()
            counts = {
                value: all_postings.filter(status=value).count()
                for value, _label in InternshipPosting.Status.choices
            }
            context['counts'] = counts
            context['posting_count'] = all_postings.count()
            context['status_tabs'] = [
                {'value': value, 'label': label, 'count': counts[value]}
                for value, label in InternshipPosting.Status.choices
            ]
        return context


class ReviewPostingsView(CoordinatorRequiredMixin, ListView):
    model = InternshipPosting
    template_name = 'opportunities/review_postings.html'
    context_object_name = 'postings'

    def get_queryset(self):
        status = self.request.GET.get('status', InternshipPosting.Status.PENDING)
        return (
            InternshipPosting.objects.filter(status=status)
            .select_related('company', 'created_by')
            .order_by('created_at')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status'] = self.request.GET.get('status', InternshipPosting.Status.PENDING)
        context['status_choices'] = InternshipPosting.Status.choices
        context['pending_count'] = InternshipPosting.objects.filter(
            status=InternshipPosting.Status.PENDING
        ).count()
        return context


class CompanyListView(ListView):
    model = Company
    template_name = 'opportunities/company_list.html'
    context_object_name = 'companies'
    paginate_by = 12

    def get_queryset(self):
        queryset = Company.objects.annotate(
            open_postings=Count(
                'postings',
                filter=Q(postings__status=InternshipPosting.Status.PUBLISHED),
            )
        )
        search = self.request.GET.get('q', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(industry__icontains=search)
                | Q(location__icontains=search)
            )
        return queryset.order_by('-is_verified', 'name')


class CompanyDetailView(DetailView):
    model = Company
    template_name = 'opportunities/company_detail.html'
    context_object_name = 'company'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['postings'] = self.object.postings.filter(
            status=InternshipPosting.Status.PUBLISHED
        )
        context['can_manage'] = is_company_representative(self.request.user, self.object)
        return context


class CompanyCreateView(EmployerRequiredMixin, CreateView):
    model = Company
    form_class = CompanyForm
    template_name = 'opportunities/company_form.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            existing = get_employer_company(request.user)
            if existing:
                messages.info(request, 'Your account is already linked to a company.')
                return redirect('opportunities:company_edit', pk=existing.pk)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        profile = self.request.user.employer_profile
        profile.company = self.object
        profile.save(update_fields=['company', 'updated_at'])
        messages.success(
            self.request,
            'Company profile created. A coordinator will verify it before your postings go live.',
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Create company profile'
        return context


class CompanyUpdateView(EmployerRequiredMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = 'opportunities/company_form.html'

    def get_queryset(self):
        queryset = Company.objects.all()
        if self.request.user.is_coordinator:
            return queryset
        company = get_employer_company(self.request.user)
        return queryset.filter(pk=company.pk) if company else queryset.none()

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Company profile updated.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Edit company profile'
        return context


@require_POST
def verify_company(request, pk):
    if not request.user.is_coordinator:
        messages.error(request, 'Only coordinators can verify companies.')
        return redirect('opportunities:company_detail', pk=pk)

    company = get_object_or_404(Company, pk=pk)
    company.is_verified = not company.is_verified
    company.verified_by = request.user if company.is_verified else None
    company.verified_at = timezone.now() if company.is_verified else None
    company.save(update_fields=['is_verified', 'verified_by', 'verified_at', 'updated_at'])

    for representative in company.representatives.select_related('user'):
        Notification.send(
            recipient=representative.user,
            title='Company verified' if company.is_verified else 'Company verification removed',
            message=f'{company.name} is {"now verified" if company.is_verified else "no longer verified"}.',
            url=reverse('opportunities:company_detail', kwargs={'pk': company.pk}),
            actor=request.user,
        )
    messages.success(
        request,
        f'{company.name} marked as {"verified" if company.is_verified else "unverified"}.',
    )
    return redirect('opportunities:company_detail', pk=pk)


@require_POST
def bookmark_toggle(request, pk):
    if not request.user.is_authenticated or not request.user.is_student:
        messages.error(request, 'Only students can save internships.')
        return redirect('opportunities:posting_detail', pk=pk)

    posting = get_object_or_404(
        InternshipPosting, pk=pk, status=InternshipPosting.Status.PUBLISHED
    )
    bookmark, created = Bookmark.objects.get_or_create(user=request.user, posting=posting)
    if created:
        messages.success(request, 'Internship saved to your list.')
    else:
        bookmark.delete()
        messages.info(request, 'Internship removed from your saved list.')

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('opportunities:posting_detail', pk=pk)


class BookmarkListView(StudentRequiredMixin, ListView):
    model = Bookmark
    template_name = 'opportunities/bookmarks.html'
    context_object_name = 'bookmarks'
    paginate_by = 12

    def get_queryset(self):
        return self.request.user.bookmarks.select_related('posting__company')
