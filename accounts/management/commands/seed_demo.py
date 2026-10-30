from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import StudentProfile, User
from applications.models import Application, ApplicationStatusHistory, Interview, Offer
from applications.services import (
    extend_offer,
    respond_to_offer,
    schedule_interview,
    transition_application,
)
from notifications.models import Notification
from opportunities.models import Bookmark, Company, InternshipPosting

DEMO_PASSWORD = 'demo12345'


class Command(BaseCommand):
    help = 'Create demo companies, students, postings, and applications.'

    def handle(self, *args, **options):
        if User.objects.filter(email='coordinator@internlink.test').exists():
            self.stdout.write(self.style.WARNING(
                'Demo data already exists. Delete db.sqlite3 to reseed from scratch.'
            ))
            return

        today = timezone.localdate()
        coordinator = User.objects.create_user(
            email='coordinator@internlink.test',
            password=DEMO_PASSWORD,
            first_name='Grace',
            last_name='Reyes',
            role=User.Role.COORDINATOR,
            phone='0917 000 0001',
        )

        northwind_rep = User.objects.create_user(
            email='employer@northwind.test',
            password=DEMO_PASSWORD,
            first_name='Daniel',
            last_name='Lim',
            role=User.Role.EMPLOYER,
        )
        northwind_rep.employer_profile.job_title = 'Talent Acquisition Lead'
        northwind_rep.employer_profile.save()

        brightwave_rep = User.objects.create_user(
            email='employer@brightwave.test',
            password=DEMO_PASSWORD,
            first_name='Nadia',
            last_name='Cruz',
            role=User.Role.EMPLOYER,
        )
        brightwave_rep.employer_profile.job_title = 'Studio Manager'
        brightwave_rep.employer_profile.save()

        northwind = Company.objects.create(
            name='Northwind Analytics',
            industry='Data & Technology',
            location='Makati City',
            website='https://northwind.example.com',
            description=(
                'Northwind Analytics builds decision-support tools for small businesses. '
                'Our interns work alongside analysts and engineers on live client projects.'
            ),
            contact_email='careers@northwind.example.com',
            contact_phone='+63 2 8888 1000',
            is_verified=True,
            verified_by=coordinator,
            verified_at=timezone.now(),
            created_by=northwind_rep,
        )
        brightwave = Company.objects.create(
            name='BrightWave Studio',
            industry='Creative & Media',
            location='Quezon City',
            website='https://brightwave.example.com',
            description=(
                'A design and content studio helping brands tell better stories. '
                'We mentor interns in design, video, and social media production.'
            ),
            contact_email='hello@brightwave.example.com',
            is_verified=True,
            verified_by=coordinator,
            verified_at=timezone.now(),
            created_by=brightwave_rep,
        )
        citygov = Company.objects.create(
            name='City Government HR Office',
            industry='Public Service',
            location='Pasig City',
            description=(
                'The city HR office coordinates internship placements across '
                'administrative, communications, and community programs.'
            ),
            contact_email='hr@citygov.example.com',
            created_by=coordinator,
        )

        northwind_rep.employer_profile.company = northwind
        northwind_rep.employer_profile.save()
        brightwave_rep.employer_profile.company = brightwave
        brightwave_rep.employer_profile.save()

        data_analyst = InternshipPosting.objects.create(
            company=northwind,
            title='Data Analyst Intern',
            description=(
                'Join our analytics team for a hands-on internship. You will help turn '
                'raw business data into clear dashboards and recommendations for clients.'
            ),
            responsibilities=(
                'Clean and prepare datasets\nBuild dashboard views in Power BI\n'
                'Document analysis steps and present findings in weekly stand-ups'
            ),
            requirements=(
                'Currently enrolled in a BS Statistics, Computer Science, or related program\n'
                'Comfortable with Excel or Google Sheets\nGood written communication skills'
            ),
            skills_required='Excel, SQL, Python, Data Visualization, Communication',
            location='Makati City',
            work_mode=InternshipPosting.WorkMode.HYBRID,
            duration_weeks=12,
            hours_per_week=24,
            stipend=12000,
            slots=2,
            application_deadline=today + timedelta(days=18),
            start_date=today + timedelta(days=30),
            status=InternshipPosting.Status.PUBLISHED,
            is_featured=True,
            created_by=northwind_rep,
            reviewed_by=coordinator,
        )
        qa_tester = InternshipPosting.objects.create(
            company=northwind,
            title='QA Automation Intern',
            description=(
                'Work with our engineering team to test web applications and build '
                'simple automated regression checks.'
            ),
            responsibilities=(
                'Write and execute manual test cases\n'
                'Maintain smoke-test scripts in Playwright\nReport defects clearly'
            ),
            requirements='Enrolled in IT or Computer Science\nBasic JavaScript knowledge',
            skills_required='JavaScript, Testing, Attention to Detail',
            location='Remote',
            work_mode=InternshipPosting.WorkMode.REMOTE,
            duration_weeks=8,
            hours_per_week=20,
            stipend=9000,
            slots=1,
            application_deadline=today + timedelta(days=9),
            start_date=today + timedelta(days=21),
            status=InternshipPosting.Status.PUBLISHED,
            created_by=northwind_rep,
            reviewed_by=coordinator,
        )
        social_media = InternshipPosting.objects.create(
            company=brightwave,
            title='Social Media Content Intern',
            description=(
                'Help plan, shoot, and publish short-form content for our retail and '
                'lifestyle clients. You will work directly with our content lead.'
            ),
            responsibilities=(
                'Draft captions and content calendars\nAssist on photo and video shoots\n'
                'Track engagement and report weekly results'
            ),
            requirements=(
                'Enrolled in Communication, Marketing, or Multimedia Arts\n'
                'Familiar with Instagram and TikTok trends'
            ),
            skills_required='Content Creation, Copywriting, Canva, Video Editing',
            location='Quezon City',
            work_mode=InternshipPosting.WorkMode.ONSITE,
            duration_weeks=10,
            hours_per_week=20,
            stipend=8000,
            slots=2,
            application_deadline=today + timedelta(days=25),
            start_date=today + timedelta(days=35),
            status=InternshipPosting.Status.PUBLISHED,
            is_featured=True,
            created_by=brightwave_rep,
            reviewed_by=coordinator,
        )
        graphic_design = InternshipPosting.objects.create(
            company=brightwave,
            title='Graphic Design Intern',
            description='Support our design team with branding, social, and print assets.',
            responsibilities='Create social graphics\nPrepare print-ready files\nJoin design critiques',
            requirements='Portfolio required\nKnowledge of Adobe Illustrator or Figma',
            skills_required='Figma, Illustrator, Typography, Layout',
            location='Quezon City',
            work_mode=InternshipPosting.WorkMode.HYBRID,
            duration_weeks=12,
            hours_per_week=16,
            stipend=7500,
            slots=1,
            application_deadline=today + timedelta(days=30),
            start_date=today + timedelta(days=40),
            status=InternshipPosting.Status.PUBLISHED,
            created_by=brightwave_rep,
            reviewed_by=coordinator,
        )
        admin_intern = InternshipPosting.objects.create(
            company=citygov,
            title='Administrative Intern',
            description='Support records management and front-desk services at the HR office.',
            responsibilities='Digitize records\nAssist walk-in clients\nPrepare simple reports',
            requirements='Enrolled in any bachelor program\nDetail-oriented and punctual',
            skills_required='Organization, Records Management, Customer Service',
            location='Pasig City',
            work_mode=InternshipPosting.WorkMode.ONSITE,
            duration_weeks=8,
            hours_per_week=24,
            stipend=0,
            slots=3,
            application_deadline=today + timedelta(days=14),
            start_date=today + timedelta(days=25),
            status=InternshipPosting.Status.PENDING,
            created_by=coordinator,
        )
        InternshipPosting.objects.create(
            company=northwind,
            title='Business Intelligence Intern',
            description='Draft posting for a future BI internship.',
            requirements='SQL, Excel',
            skills_required='SQL, Excel',
            location='Makati City',
            work_mode=InternshipPosting.WorkMode.HYBRID,
            duration_weeks=12,
            hours_per_week=20,
            stipend=10000,
            slots=1,
            application_deadline=today + timedelta(days=45),
            status=InternshipPosting.Status.DRAFT,
            created_by=northwind_rep,
        )

        alex = User.objects.create_user(
            email='student@university.test',
            password=DEMO_PASSWORD,
            first_name='Alex',
            last_name='Cruz',
            role=User.Role.STUDENT,
            phone='0917 111 2222',
        )
        alex_profile = StudentProfile.objects.get(user=alex)
        alex_profile.school = 'University of the Philippines'
        alex_profile.course = 'BS Statistics'
        alex_profile.year_level = StudentProfile.YearLevel.FOURTH
        alex_profile.location = 'Quezon City'
        alex_profile.skills = 'Python, SQL, Excel, Data Visualization, Technical Writing'
        alex_profile.bio = (
            'Statistics student who enjoys turning messy datasets into clear stories. '
            'Looking for an analytics internship where I can learn from a real team.'
        )
        alex_profile.resume.save(
            'alex-cruz-resume.txt',
            ContentFile(b'Alex Cruz - demo resume. Python, SQL, Excel, statistics coursework.'),
            save=True,
        )

        maria = User.objects.create_user(
            email='student2@university.test',
            password=DEMO_PASSWORD,
            first_name='Maria',
            last_name='Santos',
            role=User.Role.STUDENT,
            phone='0917 333 4444',
        )
        maria_profile = StudentProfile.objects.get(user=maria)
        maria_profile.school = 'Ateneo de Manila University'
        maria_profile.course = 'AB Communication'
        maria_profile.year_level = StudentProfile.YearLevel.THIRD
        maria_profile.location = 'Marikina City'
        maria_profile.skills = 'Copywriting, Canva, Video Editing, Social Media'
        maria_profile.bio = 'Communication student passionate about short-form video and brand storytelling.'
        maria_profile.resume.save(
            'maria-santos-resume.txt',
            ContentFile(b'Maria Santos - demo resume. Content creation and communication coursework.'),
            save=True,
        )

        application = Application.objects.create(
            posting=data_analyst,
            student=alex,
            cover_letter=(
                'I have used Python and SQL in my statistics coursework and built '
                'dashboards for our student council. I would love to contribute to '
                'Northwind client projects while learning from your analysts.'
            ),
            resume=alex_profile.resume,
        )
        ApplicationStatusHistory.objects.create(
            application=application,
            from_status='',
            to_status=Application.Status.SUBMITTED,
            changed_by=alex,
            note='Application submitted.',
        )
        Notification.send(
            recipient=northwind_rep,
            title='New application received',
            message='Alex Cruz applied for Data Analyst Intern.',
            url=f'/applications/{application.pk}/',
            actor=alex,
        )
        transition_application(application, Application.Status.UNDER_REVIEW, northwind_rep)
        transition_application(application, Application.Status.SHORTLISTED, northwind_rep,
                               note='Strong coursework and a clear portfolio.')
        interview = Interview.objects.create(
            application=application,
            scheduled_at=timezone.now() + timedelta(days=4, hours=2),
            mode=Interview.Mode.ONLINE,
            location='https://meet.example.com/northwind-analyst',
            notes='30-minute conversation with the analytics lead.',
            created_by=northwind_rep,
        )
        transition_application(
            application,
            Application.Status.INTERVIEW,
            northwind_rep,
            note=f'Interview scheduled for {interview.scheduled_at:%b %d, %Y %H:%M}.',
        )

        maria_application = Application.objects.create(
            posting=social_media,
            student=maria,
            cover_letter=(
                'I run a small food blog with 4,000 followers and have edited short videos '
                'for two campus organizations. I would love to bring that experience to BrightWave.'
            ),
            resume=maria_profile.resume,
        )
        ApplicationStatusHistory.objects.create(
            application=maria_application,
            from_status='',
            to_status=Application.Status.SUBMITTED,
            changed_by=maria,
            note='Application submitted.',
        )
        Notification.send(
            recipient=brightwave_rep,
            title='New application received',
            message='Maria Santos applied for Social Media Content Intern.',
            url=f'/applications/{maria_application.pk}/',
            actor=maria,
        )
        transition_application(maria_application, Application.Status.UNDER_REVIEW, brightwave_rep)
        transition_application(maria_application, Application.Status.SHORTLISTED, brightwave_rep)

        accepted_application = Application.objects.create(
            posting=qa_tester,
            student=maria,
            cover_letter='I enjoy finding edge cases and have basic JavaScript experience.',
            resume=maria_profile.resume,
        )
        ApplicationStatusHistory.objects.create(
            application=accepted_application,
            from_status='',
            to_status=Application.Status.SUBMITTED,
            changed_by=maria,
            note='Application submitted.',
        )
        for status in (
            Application.Status.UNDER_REVIEW,
            Application.Status.SHORTLISTED,
            Application.Status.INTERVIEW,
        ):
            transition_application(accepted_application, status, northwind_rep)
        offer = Offer.objects.create(
            application=accepted_application,
            start_date=today + timedelta(days=21),
            end_date=today + timedelta(days=21 + 56),
            stipend=9000,
            details='Remote QA internship, 20 hours per week, with weekly check-ins.',
            response_deadline=today + timedelta(days=5),
            offered_by=northwind_rep,
        )
        transition_application(accepted_application, Application.Status.OFFERED, northwind_rep,
                               note='Internship offer extended.')
        respond_to_offer(accepted_application, True, maria)

        Bookmark.objects.create(user=alex, posting=graphic_design)
        Bookmark.objects.create(user=alex, posting=social_media)
        Bookmark.objects.create(user=maria, posting=data_analyst)

        Notification.send(
            recipient=coordinator,
            title='Posting awaiting review',
            message='City Government HR Office submitted "Administrative Intern" for review.',
            url=f'/opportunities/{admin_intern.pk}/',
            actor=coordinator,
        )

        self.stdout.write(self.style.SUCCESS('Demo data created.'))
        self.stdout.write('')
        self.stdout.write('Demo accounts (password: demo12345)')
        self.stdout.write('  Coordinator : coordinator@internlink.test')
        self.stdout.write('  Employer    : employer@northwind.test')
        self.stdout.write('  Employer    : employer@brightwave.test')
        self.stdout.write('  Student     : student@university.test')
        self.stdout.write('  Student     : student2@university.test')
