from django.test import TestCase
from django.urls import reverse

from notifications.models import Notification

from .models import CoordinatorRequest, EmployerProfile, StudentProfile, User


class RegistrationTests(TestCase):
    def test_student_registration_creates_profile(self):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'first_name': 'Sam',
                'last_name': 'Student',
                'email': 'sam@test.com',
                'role': User.Role.STUDENT,
                'password1': 'a-very-strong-pass-123',
                'password2': 'a-very-strong-pass-123',
            },
        )
        self.assertRedirects(response, reverse('dashboard:home'))
        user = User.objects.get(email='sam@test.com')
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())
        self.assertEqual(user.role, User.Role.STUDENT)

    def test_employer_registration_creates_profile(self):
        self.client.post(
            reverse('accounts:register'),
            {
                'first_name': 'Erin',
                'last_name': 'Employer',
                'email': 'erin@test.com',
                'role': User.Role.EMPLOYER,
                'password1': 'a-very-strong-pass-123',
                'password2': 'a-very-strong-pass-123',
            },
        )
        user = User.objects.get(email='erin@test.com')
        self.assertTrue(EmployerProfile.objects.filter(user=user).exists())

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email='sam@test.com', password='pass12345')
        response = self.client.post(
            reverse('accounts:register'),
            {
                'first_name': 'Sam',
                'last_name': 'Other',
                'email': 'sam@test.com',
                'role': User.Role.STUDENT,
                'password1': 'a-very-strong-pass-123',
                'password2': 'a-very-strong-pass-123',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email='sam@test.com').count(), 1)

    def test_login_uses_email(self):
        user = User.objects.create_user(email='sam@test.com', password='pass12345')
        response = self.client.post(
            reverse('accounts:login'),
            {'username': 'sam@test.com', 'password': 'pass12345'},
        )
        self.assertRedirects(response, reverse('dashboard:home'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_profile_edit_updates_student_details(self):
        user = User.objects.create_user(
            email='sam@test.com', password='pass12345', role=User.Role.STUDENT
        )
        self.client.force_login(user)
        response = self.client.post(
            reverse('accounts:profile_edit'),
            {
                'first_name': 'Sam',
                'last_name': 'Updated',
                'phone': '0917',
                'school': 'State University',
                'course': 'Computer Science',
                'year_level': '4',
                'location': 'Manila',
                'skills': 'Python, SQL',
                'bio': 'Hello',
                'linkedin_url': '',
                'portfolio_url': '',
            },
        )
        self.assertRedirects(response, reverse('accounts:profile'))
        user.refresh_from_db()
        self.assertEqual(user.last_name, 'Updated')
        self.assertEqual(user.student_profile.school, 'State University')


class CoordinatorRequestTests(TestCase):
    def setUp(self):
        self.coordinator = User.objects.create_user(
            email='coord@test.com',
            password='pass12345',
            first_name='Grace',
            last_name='Reyes',
            role=User.Role.COORDINATOR,
        )
        self.payload = {
            'full_name': 'Ada Cruz',
            'institution': 'State University',
            'email': 'ada@state.edu',
            'message': 'Internship office staff.',
        }

    def test_anonymous_can_submit_a_request(self):
        response = self.client.post(reverse('accounts:coordinator_request'), self.payload)
        self.assertRedirects(
            response, f"{reverse('accounts:coordinator_request')}?sent=1"
        )
        access_request = CoordinatorRequest.objects.get(email='ada@state.edu')
        self.assertEqual(access_request.status, CoordinatorRequest.Status.PENDING)
        self.assertTrue(
            Notification.objects.filter(recipient=self.coordinator).exists()
        )

    def test_duplicate_pending_request_is_rejected(self):
        CoordinatorRequest.objects.create(**self.payload)
        response = self.client.post(reverse('accounts:coordinator_request'), self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            CoordinatorRequest.objects.filter(email='ada@state.edu').count(), 1
        )

    def test_existing_account_email_is_rejected(self):
        self.payload['email'] = self.coordinator.email
        response = self.client.post(reverse('accounts:coordinator_request'), self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CoordinatorRequest.objects.count(), 0)

    def test_non_coordinator_cannot_approve(self):
        student = User.objects.create_user(
            email='student@test.com', password='pass12345', role=User.Role.STUDENT
        )
        access_request = CoordinatorRequest.objects.create(**self.payload)
        self.client.force_login(student)
        response = self.client.post(
            reverse('accounts:coordinator_request_approve', args=[access_request.pk])
        )
        self.assertRedirects(response, reverse('dashboard:home'))
        access_request.refresh_from_db()
        self.assertEqual(access_request.status, CoordinatorRequest.Status.PENDING)
        self.assertFalse(User.objects.filter(email='ada@state.edu').exists())

    def test_approval_creates_a_coordinator_and_invite_link(self):
        access_request = CoordinatorRequest.objects.create(**self.payload)
        self.client.force_login(self.coordinator)
        response = self.client.post(
            reverse('accounts:coordinator_request_approve', args=[access_request.pk])
        )
        self.assertRedirects(response, reverse('dashboard:home'))

        access_request.refresh_from_db()
        self.assertEqual(access_request.status, CoordinatorRequest.Status.APPROVED)
        self.assertIsNotNone(access_request.invite_token)
        self.assertEqual(access_request.reviewed_by, self.coordinator)

        user = User.objects.get(email='ada@state.edu')
        self.assertEqual(user.role, User.Role.COORDINATOR)
        self.assertEqual(user.first_name, 'Ada')
        self.assertEqual(user.last_name, 'Cruz')
        self.assertFalse(user.has_usable_password())

    def test_invite_link_sets_the_password_and_signs_in(self):
        access_request = CoordinatorRequest.objects.create(**self.payload)
        self.client.force_login(self.coordinator)
        self.client.post(
            reverse('accounts:coordinator_request_approve', args=[access_request.pk])
        )
        self.client.logout()
        access_request.refresh_from_db()

        url = reverse(
            'accounts:coordinator_invite', args=[access_request.invite_token]
        )
        self.assertEqual(self.client.get(url).status_code, 200)

        response = self.client.post(
            url, {'new_password1': 'brand-new-pass-4821', 'new_password2': 'brand-new-pass-4821'}
        )
        self.assertRedirects(response, reverse('dashboard:home'))

        user = User.objects.get(email='ada@state.edu')
        self.assertTrue(user.check_password('brand-new-pass-4821'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

        access_request.refresh_from_db()
        self.assertIsNone(access_request.invite_token)
        # The link cannot be reused.
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_reject_marks_the_request_rejected(self):
        access_request = CoordinatorRequest.objects.create(**self.payload)
        self.client.force_login(self.coordinator)
        self.client.post(
            reverse('accounts:coordinator_request_reject', args=[access_request.pk])
        )
        access_request.refresh_from_db()
        self.assertEqual(access_request.status, CoordinatorRequest.Status.REJECTED)
        self.assertEqual(access_request.reviewed_by, self.coordinator)
        self.assertFalse(User.objects.filter(email='ada@state.edu').exists())
