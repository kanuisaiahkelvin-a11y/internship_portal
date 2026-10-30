from django.test import TestCase
from django.urls import reverse

from .models import EmployerProfile, StudentProfile, User


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
