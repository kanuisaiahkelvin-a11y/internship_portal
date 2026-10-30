from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from .models import Bookmark, Company, InternshipPosting


class PostingTests(TestCase):
    def setUp(self):
        self.coordinator = User.objects.create_user(
            email='coord@test.com', password='pass12345', role=User.Role.COORDINATOR
        )
        self.employer = User.objects.create_user(
            email='employer@test.com', password='pass12345', role=User.Role.EMPLOYER
        )
        self.company = Company.objects.create(
            name='Acme Corp', location='Manila', created_by=self.employer
        )
        self.employer.employer_profile.company = self.company
        self.employer.employer_profile.save()
        self.student = User.objects.create_user(
            email='student@test.com', password='pass12345', role=User.Role.STUDENT
        )
        self.posting = InternshipPosting.objects.create(
            company=self.company,
            title='Analyst Intern',
            description='Analyze things.',
            location='Manila',
            duration_weeks=8,
            hours_per_week=20,
            slots=1,
            application_deadline=timezone.localdate() + timedelta(days=10),
            status=InternshipPosting.Status.PUBLISHED,
            created_by=self.employer,
        )

    def test_only_published_postings_are_public(self):
        draft = InternshipPosting.objects.create(
            company=self.company,
            title='Draft Intern',
            description='Hidden.',
            location='Manila',
            duration_weeks=8,
            hours_per_week=20,
            slots=1,
            application_deadline=timezone.localdate() + timedelta(days=10),
            status=InternshipPosting.Status.DRAFT,
            created_by=self.employer,
        )
        self.client.force_login(self.student)
        self.assertEqual(
            self.client.get(reverse('opportunities:posting_detail', args=[self.posting.pk])).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse('opportunities:posting_detail', args=[draft.pk])).status_code,
            404,
        )

    def test_owner_can_view_own_draft(self):
        draft = InternshipPosting.objects.create(
            company=self.company,
            title='Draft Intern',
            description='Hidden.',
            location='Manila',
            duration_weeks=8,
            hours_per_week=20,
            slots=1,
            application_deadline=timezone.localdate() + timedelta(days=10),
            status=InternshipPosting.Status.DRAFT,
            created_by=self.employer,
        )
        self.client.force_login(self.employer)
        response = self.client.get(reverse('opportunities:posting_detail', args=[draft.pk]))
        self.assertEqual(response.status_code, 200)

    def test_submit_and_approve_posting(self):
        self.posting.status = InternshipPosting.Status.DRAFT
        self.posting.save()
        self.client.force_login(self.employer)
        self.client.post(reverse('opportunities:posting_submit', args=[self.posting.pk]))
        self.posting.refresh_from_db()
        self.assertEqual(self.posting.status, InternshipPosting.Status.PENDING)

        self.client.force_login(self.coordinator)
        self.client.post(reverse('opportunities:posting_approve', args=[self.posting.pk]))
        self.posting.refresh_from_db()
        self.assertEqual(self.posting.status, InternshipPosting.Status.PUBLISHED)
        self.assertEqual(self.posting.reviewed_by, self.coordinator)

    def test_student_cannot_submit_posting(self):
        self.posting.status = InternshipPosting.Status.DRAFT
        self.posting.save()
        self.client.force_login(self.student)
        self.client.post(reverse('opportunities:posting_submit', args=[self.posting.pk]))
        self.posting.refresh_from_db()
        self.assertEqual(self.posting.status, InternshipPosting.Status.DRAFT)

    def test_bookmark_toggle(self):
        self.client.force_login(self.student)
        url = reverse('opportunities:bookmark_toggle', args=[self.posting.pk])
        self.client.post(url)
        self.assertEqual(Bookmark.objects.filter(user=self.student).count(), 1)
        self.client.post(url)
        self.assertEqual(Bookmark.objects.filter(user=self.student).count(), 0)

    def test_employer_cannot_create_posting_without_company(self):
        lonely = User.objects.create_user(
            email='lonely@test.com', password='pass12345', role=User.Role.EMPLOYER
        )
        self.client.force_login(lonely)
        response = self.client.get(reverse('opportunities:posting_create'))
        self.assertRedirects(response, reverse('opportunities:company_create'))

    def test_coordinator_verifies_company(self):
        self.assertFalse(self.company.is_verified)
        self.client.force_login(self.coordinator)
        self.client.post(reverse('opportunities:company_verify', args=[self.company.pk]))
        self.company.refresh_from_db()
        self.assertTrue(self.company.is_verified)
        self.assertEqual(self.company.verified_by, self.coordinator)

    def test_posting_list_filters(self):
        response = self.client.get(reverse('opportunities:posting_list'), {'q': 'Analyst'})
        self.assertContains(response, 'Analyst Intern')
        response = self.client.get(reverse('opportunities:posting_list'), {'q': 'Nothing'})
        self.assertNotContains(response, 'Analyst Intern')
