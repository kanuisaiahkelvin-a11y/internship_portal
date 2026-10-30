from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from accounts.mixins import CoordinatorRequiredMixin
from accounts.models import User
from applications.models import Application, Interview
from opportunities.models import Company, InternshipPosting
from django.views.generic import TemplateView


def home(request):
    user = request.user
    today = timezone.localdate()

    if not user.is_authenticated:
        postings = (
            InternshipPosting.objects.filter(
                status=InternshipPosting.Status.PUBLISHED,
                application_deadline__gte=today,
            )
            .select_related('company')
            .order_by('-is_featured', '-created_at')[:6]
        )
        return render(
            request,
            'dashboard/landing.html',
            {
                'postings': postings,
                'company_count': Company.objects.count(),
                'posting_count': InternshipPosting.objects.filter(
                    status=InternshipPosting.Status.PUBLISHED
                ).count(),
                'student_count': User.objects.filter(role=User.Role.STUDENT).count(),
            },
        )

    if user.is_student:
        applications = Application.objects.filter(student=user).select_related(
            'posting__company'
        )
        applied_posting_ids = applications.values_list('posting_id', flat=True)
        recommended = (
            InternshipPosting.objects.filter(
                status=InternshipPosting.Status.PUBLISHED,
                application_deadline__gte=today,
            )
            .exclude(pk__in=applied_posting_ids)
            .select_related('company')
            .order_by('-is_featured', '-created_at')[:3]
        )
        upcoming_interviews = (
            Interview.objects.filter(
                application__student=user,
                status=Interview.Status.SCHEDULED,
                scheduled_at__gte=timezone.now(),
            )
            .select_related('application__posting__company')
            .order_by('scheduled_at')[:5]
        )
        return render(
            request,
            'dashboard/student_home.html',
            {
                'applications': applications[:5],
                'application_count': applications.count(),
                'active_count': applications.exclude(
                    status__in=[
                        Application.Status.ACCEPTED,
                        Application.Status.REJECTED,
                        Application.Status.WITHDRAWN,
                    ]
                ).count(),
                'offer_count': applications.filter(
                    status=Application.Status.OFFERED
                ).count(),
                'accepted_count': applications.filter(
                    status=Application.Status.ACCEPTED
                ).count(),
                'recommended': recommended,
                'upcoming_interviews': upcoming_interviews,
                'saved_count': user.bookmarks.count(),
                'profile': getattr(user, 'student_profile', None),
            },
        )

    if user.is_employer:
        profile = getattr(user, 'employer_profile', None)
        company = profile.company if profile else None
        postings = company.postings.all() if company else InternshipPosting.objects.none()
        applications = (
            Application.objects.filter(posting__company=company).select_related(
                'student', 'posting'
            )
            if company
            else Application.objects.none()
        )
        upcoming_interviews = (
            Interview.objects.filter(
                application__posting__company=company,
                status=Interview.Status.SCHEDULED,
                scheduled_at__gte=timezone.now(),
            )
            .select_related('application__student', 'application__posting')
            .order_by('scheduled_at')[:5]
            if company
            else Interview.objects.none()
        )
        return render(
            request,
            'dashboard/employer_home.html',
            {
                'company': company,
                'postings': postings[:5],
                'posting_count': postings.count(),
                'published_count': postings.filter(
                    status=InternshipPosting.Status.PUBLISHED
                ).count(),
                'pending_count': postings.filter(
                    status=InternshipPosting.Status.PENDING
                ).count(),
                'applications': applications[:8],
                'application_count': applications.count(),
                'new_application_count': applications.filter(
                    status=Application.Status.SUBMITTED
                ).count(),
                'shortlisted_count': applications.filter(
                    status__in=[
                        Application.Status.SHORTLISTED,
                        Application.Status.INTERVIEW,
                    ]
                ).count(),
                'upcoming_interviews': upcoming_interviews,
            },
        )

    # Coordinator dashboard
    applications = Application.objects.select_related('student', 'posting__company')
    status_counts = {
        row['status']: row['total']
        for row in applications.values('status').annotate(total=Count('id'))
    }
    company_rows = (
        Company.objects.annotate(
            posting_total=Count('postings', distinct=True),
            application_total=Count('postings__applications', distinct=True),
            accepted_total=Count(
                'postings__applications',
                filter=Q(postings__applications__status=Application.Status.ACCEPTED),
                distinct=True,
            ),
        )
        .order_by('-application_total', 'name')[:8]
    )
    return render(
        request,
        'dashboard/coordinator_home.html',
        {
            'pending_postings': InternshipPosting.objects.filter(
                status=InternshipPosting.Status.PENDING
            ).select_related('company', 'created_by'),
            'pending_count': InternshipPosting.objects.filter(
                status=InternshipPosting.Status.PENDING
            ).count(),
            'unverified_companies': Company.objects.filter(is_verified=False).count(),
            'application_count': applications.count(),
            'status_counts': status_counts,
            'recent_applications': applications.order_by('-created_at')[:8],
            'company_rows': company_rows,
            'student_count': User.objects.filter(role=User.Role.STUDENT).count(),
            'company_count': Company.objects.count(),
            'placed_count': applications.filter(
                status=Application.Status.ACCEPTED
            ).values('student').distinct().count(),
        },
    )


class ReportsView(CoordinatorRequiredMixin, TemplateView):
    template_name = 'dashboard/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        applications = Application.objects.all()
        total = applications.count()
        status_counts = [
            {
                'status': status,
                'label': dict(Application.Status.choices)[status],
                'total': applications.filter(status=status).count(),
            }
            for status in Application.Status.values
        ]
        accepted = applications.filter(status=Application.Status.ACCEPTED).count()

        context.update(
            {
                'total_applications': total,
                'status_counts': status_counts,
                'accepted_count': accepted,
                'placed_students': applications.filter(
                    status=Application.Status.ACCEPTED
                ).values('student').distinct().count(),
                'placement_rate': round((accepted / total) * 100, 1) if total else 0,
                'posting_counts': {
                    row['status']: row['total']
                    for row in InternshipPosting.objects.values('status').annotate(
                        total=Count('id')
                    )
                },
                'company_rows': Company.objects.annotate(
                    posting_total=Count('postings', distinct=True),
                    application_total=Count('postings__applications', distinct=True),
                    accepted_total=Count(
                        'postings__applications',
                        filter=Q(postings__applications__status=Application.Status.ACCEPTED),
                        distinct=True,
                    ),
                ).order_by('-application_total', 'name'),
                'monthly': list(
                    applications.annotate(month=TruncMonth('created_at'))
                    .values('month')
                    .annotate(total=Count('id'))
                    .order_by('month')[:12]
                ),
                'top_postings': InternshipPosting.objects.annotate(
                    application_total=Count('applications')
                ).order_by('-application_total')[:10],
            }
        )
        return context
