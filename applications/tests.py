from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import StudentProfile, User
from notifications.models import Notification
from opportunities.models import Company, InternshipPosting

from .models import Application, Offer
from .services import InvalidTransition, respond_to_offer, transition_application


class ApplicationTestCase(TestCase):
    def setUp(self):
        self.coordinator = User.objects.create_user(
            email='coord@test.com', password='pass12345', role=User.Role.COORDINATOR
        )
        self.employer = User.objects.create_user(
            email='employer@test.com', password='pass12345',
            first_name='Erin', last_name='Employer', role=User.Role.EMPLOYER,
        )
        self.company = Company.objects.create(
            name='Acme Corp', location='Manila', created_by=self.employer
        )
        self.employer.employer_profile.company = self.company
        self.employer.employer_profile.save()

        self.student = User.objects.create_user(
            email='student@test.com', password='pass12345',
            first_name='Sam', last_name='Student', role=User.Role.STUDENT,
        )
        self.student_profile = StudentProfile.objects.get(user=self.student)
        self.student_profile.resume = SimpleUploadedFile('resume.pdf', b'%PDF-1.4 demo')
        self.student_profile.save()

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

    def apply(self):
        return self.client.post(
            reverse('applications:apply', args=[self.posting.pk]),
            {
                'cover_letter': 'I am interested.',
                'resume': SimpleUploadedFile('cv.pdf', b'%PDF-1.4 cv'),
            },
        )

    def test_student_can_apply(self):
        self.client.force_login(self.student)
        response = self.apply()
        application = Application.objects.get(posting=self.posting, student=self.student)
        self.assertRedirects(response, reverse('applications:detail', args=[application.pk]))
        self.assertEqual(application.status, Application.Status.SUBMITTED)
        self.assertTrue(Notification.objects.filter(recipient=self.employer).exists())

    def test_duplicate_application_blocked(self):
        self.client.force_login(self.student)
        self.apply()
        self.apply()
        self.assertEqual(Application.objects.count(), 1)

    def test_apply_uses_profile_resume_when_no_upload(self):
        self.client.force_login(self.student)
        self.client.post(
            reverse('applications:apply', args=[self.posting.pk]),
            {'cover_letter': 'Using my profile resume.'},
        )
        application = Application.objects.get(student=self.student)
        self.assertTrue(application.resume.name.endswith('.pdf'))

    def test_closed_posting_cannot_be_applied_to(self):
        self.posting.status = InternshipPosting.Status.CLOSED
        self.posting.save()
        self.client.force_login(self.student)
        response = self.client.get(reverse('applications:apply', args=[self.posting.pk]))
        self.assertEqual(response.status_code, 404)

    def test_employer_transitions_application(self):
        application = Application.objects.create(
            posting=self.posting, student=self.student, resume='resumes/cv.pdf'
        )
        self.client.force_login(self.employer)
        response = self.client.post(
            reverse('applications:update_status', args=[application.pk]),
            {'new_status': Application.Status.UNDER_REVIEW, 'note': 'Looks good.'},
        )
        self.assertRedirects(response, reverse('applications:detail', args=[application.pk]))
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.UNDER_REVIEW)
        self.assertTrue(application.status_history.exists())

    def test_invalid_transition_rejected(self):
        application = Application.objects.create(
            posting=self.posting, student=self.student, resume='resumes/cv.pdf'
        )
        self.client.force_login(self.employer)
        self.client.post(
            reverse('applications:update_status', args=[application.pk]),
            {'new_status': Application.Status.ACCEPTED},
        )
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.SUBMITTED)

    def test_other_employer_cannot_view_application(self):
        other = User.objects.create_user(
            email='other@test.com', password='pass12345', role=User.Role.EMPLOYER
        )
        other_company = Company.objects.create(name='Other Co', location='Cebu', created_by=other)
        other.employer_profile.company = other_company
        other.employer_profile.save()
        application = Application.objects.create(
            posting=self.posting, student=self.student, resume='resumes/cv.pdf'
        )
        self.client.force_login(other)
        response = self.client.get(reverse('applications:detail', args=[application.pk]))
        self.assertEqual(response.status_code, 404)

    def test_coordinator_can_view_any_application(self):
        application = Application.objects.create(
            posting=self.posting, student=self.student, resume='resumes/cv.pdf'
        )
        self.client.force_login(self.coordinator)
        response = self.client.get(reverse('applications:detail', args=[application.pk]))
        self.assertEqual(response.status_code, 200)

    def test_student_can_withdraw(self):
        application = Application.objects.create(
            posting=self.posting, student=self.student, resume='resumes/cv.pdf'
        )
        self.client.force_login(self.student)
        self.client.post(reverse('applications:withdraw', args=[application.pk]))
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.WITHDRAWN)

    def test_offer_acceptance_flow(self):
        application = Application.objects.create(
            posting=self.posting, student=self.student, resume='resumes/cv.pdf'
        )
        for status in (
            Application.Status.UNDER_REVIEW,
            Application.Status.SHORTLISTED,
            Application.Status.OFFERED,
        ):
            transition_application(application, status, self.employer)
        Offer.objects.create(
            application=application,
            start_date=timezone.localdate() + timedelta(days=14),
            stipend=5000,
            offered_by=self.employer,
        )
        self.client.force_login(self.student)
        self.client.post(
            reverse('applications:respond_offer', args=[application.pk]),
            {'decision': 'accept'},
        )
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.ACCEPTED)

    def test_cannot_transition_after_acceptance(self):
        application = Application.objects.create(
            posting=self.posting, student=self.student, resume='resumes/cv.pdf',
            status=Application.Status.ACCEPTED,
        )
        with self.assertRaises(InvalidTransition):
            transition_application(
                application, Application.Status.REJECTED, self.employer
            )

    def test_anonymous_redirected_from_application_detail(self):
        application = Application.objects.create(
            posting=self.posting, student=self.student, resume='resumes/cv.pdf'
        )
        response = self.client.get(reverse('applications:detail', args=[application.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_review_list_scoped_for_employer(self):
        Application.objects.create(
            posting=self.posting, student=self.student, resume='resumes/cv.pdf'
        )
        self.client.force_login(self.employer)
        response = self.client.get(reverse('applications:review_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Analyst Intern')

    def test_student_cannot_access_review_list(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse('applications:review_list'))
        self.assertRedirects(response, reverse('dashboard:home'))
