from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from applications.models import Application
from opportunities.models import Company, InternshipPosting


class DashboardTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            email='student@test.com', password='pass12345',
            first_name='Sam', last_name='Student', role=User.Role.STUDENT,
        )
        self.employer = User.objects.create_user(
            email='employer@test.com', password='pass12345',
            first_name='Erin', last_name='Employer', role=User.Role.EMPLOYER,
        )
        self.coordinator = User.objects.create_user(
            email='coord@test.com', password='pass12345',
            first_name='Grace', last_name='Reyes', role=User.Role.COORDINATOR,
        )

    def test_landing_page_renders_for_anonymous(self):
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Find the right place')

    def test_landing_page_describes_the_two_portals(self):
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'One platform, two portals')
        self.assertContains(response, 'Student portal')
        self.assertContains(response, 'Company / employer portal')
        self.assertNotContains(response, 'University / admin portal')
        self.assertNotContains(response, 'Request coordinator access')

    def test_each_role_dashboard_renders(self):
        for user in (self.student, self.employer, self.coordinator):
            self.client.force_login(user)
            response = self.client.get(reverse('dashboard:home'))
            self.assertEqual(response.status_code, 200, user.email)

    def test_reports_requires_coordinator(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('dashboard:reports'))
        self.assertRedirects(response, reverse('dashboard:home'))
        self.client.force_login(self.coordinator)
        response = self.client.get(reverse('dashboard:reports'))
        self.assertEqual(response.status_code, 200)

    def test_public_pages_render(self):
        for url in (
            reverse('opportunities:posting_list'),
            reverse('opportunities:company_list'),
            reverse('accounts:login'),
            reverse('accounts:register'),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

    def test_authenticated_pages_render(self):
        self.client.force_login(self.student)
        for url in (
            reverse('applications:my_applications'),
            reverse('opportunities:bookmark_list'),
            reverse('notifications:list'),
            reverse('accounts:profile'),
            reverse('accounts:profile_edit'),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

        self.client.force_login(self.employer)
        for url in (
            reverse('opportunities:my_postings'),
            reverse('applications:review_list'),
            reverse('opportunities:company_create'),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

        self.client.force_login(self.coordinator)
        for url in (
            reverse('opportunities:review_postings'),
            reverse('applications:review_list'),
            reverse('dashboard:reports'),
            reverse('dashboard:student_records'),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)


class StudentRecordsTests(TestCase):
    def setUp(self):
        self.coordinator = User.objects.create_user(
            email='coord@test.com', password='pass12345',
            first_name='Grace', last_name='Reyes', role=User.Role.COORDINATOR,
        )
        self.employer = User.objects.create_user(
            email='employer@test.com', password='pass12345',
            first_name='Erin', last_name='Employer', role=User.Role.EMPLOYER,
        )
        self.student = User.objects.create_user(
            email='student@test.com', password='pass12345',
            first_name='Sam', last_name='Student', role=User.Role.STUDENT,
        )
        self.company = Company.objects.create(
            name='Acme Corp', location='Manila', created_by=self.employer
        )
        self.posting = InternshipPosting.objects.create(
            company=self.company,
            title='Analyst Intern',
            description='Analyze things.',
            location='Manila',
            application_deadline=timezone.localdate() + timedelta(days=10),
            status=InternshipPosting.Status.PUBLISHED,
            created_by=self.employer,
        )
        self.application = Application.objects.create(
            posting=self.posting,
            student=self.student,
            resume=SimpleUploadedFile('cv.pdf', b'%PDF-1.4 cv'),
            status=Application.Status.ACCEPTED,
        )

    def test_coordinator_can_view_student_records(self):
        self.client.force_login(self.coordinator)
        response = self.client.get(reverse('dashboard:student_records'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sam Student')
        self.assertContains(response, 'Acme Corp')
        self.assertContains(response, 'Analyst Intern')
        self.assertContains(response, 'Placed')

    def test_student_cannot_view_student_records(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('dashboard:student_records'))
        self.assertRedirects(response, reverse('dashboard:home'))

    def test_coordinator_can_open_a_student_record(self):
        self.client.force_login(self.coordinator)
        response = self.client.get(
            reverse('dashboard:student_record_detail', args=[self.student.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Internship record')
        self.assertContains(response, 'Analyst Intern')
        self.assertContains(response, 'Acme Corp')

    def test_record_detail_is_limited_to_students(self):
        self.client.force_login(self.coordinator)
        response = self.client.get(
            reverse('dashboard:student_record_detail', args=[self.employer.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_search_filters_students(self):
        User.objects.create_user(
            email='other@test.com', password='pass12345',
            first_name='Other', last_name='Person', role=User.Role.STUDENT,
        )
        self.client.force_login(self.coordinator)
        response = self.client.get(
            reverse('dashboard:student_records'), {'q': 'Sam'}
        )
        self.assertContains(response, 'Sam Student')
        self.assertNotContains(response, 'Other Person')
