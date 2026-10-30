from django.test import TestCase
from django.urls import reverse

from accounts.models import User


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

    def test_landing_page_describes_the_three_portals(self):
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'One platform, three portals')
        self.assertContains(response, 'Student portal')
        self.assertContains(response, 'Company / employer portal')
        self.assertContains(response, 'University / admin portal')
        self.assertContains(response, 'Post internships and manage applicants')
        self.assertContains(response, 'Monitor students and placements')

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
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
