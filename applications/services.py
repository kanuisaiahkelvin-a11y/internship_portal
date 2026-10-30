from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification

from .models import Application, ApplicationStatusHistory, Offer


class InvalidTransition(Exception):
    pass


def _application_url(application):
    return reverse('applications:detail', kwargs={'pk': application.pk})


def _notify_company(application, title, message, actor):
    company = application.posting.company
    for representative in company.representatives.select_related('user'):
        Notification.send(
            recipient=representative.user,
            title=title,
            message=message,
            url=_application_url(application),
            actor=actor,
        )


def notify_new_application(application):
    _notify_company(
        application,
        title='New application received',
        message=(
            f'{application.student.full_name} applied for {application.posting.title}.'
        ),
        actor=application.student,
    )


def transition_application(application, new_status, user, note=''):
    """Move an application through the review pipeline, log it, and notify."""
    if new_status == application.status:
        return application
    if not application.can_transition_to(new_status):
        raise InvalidTransition(
            f'An application cannot move from '
            f'{application.get_status_display()} to {dict(Application.Status.choices)[new_status]}.'
        )

    from_status = application.status
    application.status = new_status
    application.save(update_fields=['status', 'updated_at'])
    ApplicationStatusHistory.objects.create(
        application=application,
        from_status=from_status,
        to_status=new_status,
        changed_by=user,
        note=note,
    )

    status_label = application.get_status_display()
    if user.pk != application.student_id:
        Notification.send(
            recipient=application.student,
            title=f'Application update: {status_label}',
            message=(
                f'Your application for {application.posting.title} at '
                f'{application.posting.company.name} is now "{status_label}".'
            ),
            url=_application_url(application),
            actor=user,
        )
    else:
        _notify_company(
            application,
            title=f'Application {status_label.lower()}',
            message=(
                f'{application.student.full_name} {status_label.lower()} the application for '
                f'{application.posting.title}.'
            ),
            actor=user,
        )
    return application


def schedule_interview(application, form, user):
    interview = form.save(commit=False)
    interview.application = application
    interview.created_by = user
    interview.save()

    if application.status != Application.Status.INTERVIEW:
        transition_application(
            application,
            Application.Status.INTERVIEW,
            user,
            note=f'Interview scheduled for {interview.scheduled_at:%b %d, %Y %H:%M}.',
        )
    else:
        Notification.send(
            recipient=application.student,
            title='Interview scheduled',
            message=(
                f'An interview for {application.posting.title} is scheduled for '
                f'{interview.scheduled_at:%b %d, %Y %H:%M}.'
            ),
            url=_application_url(application),
            actor=user,
        )
    return interview


def extend_offer(application, form, user):
    offer = form.save(commit=False)
    offer.application = application
    offer.offered_by = user
    offer.save()

    if application.status != Application.Status.OFFERED:
        transition_application(
            application,
            Application.Status.OFFERED,
            user,
            note='Internship offer extended.',
        )
    else:
        Notification.send(
            recipient=application.student,
            title='Offer extended',
            message=f'You received an internship offer for {application.posting.title}.',
            url=_application_url(application),
            actor=user,
        )
    return offer


def respond_to_offer(application, accept, user):
    offer = getattr(application, 'offer', None)
    if offer is None or application.status != Application.Status.OFFERED:
        raise InvalidTransition('There is no pending offer to respond to.')

    offer.responded_at = timezone.now()
    offer.save(update_fields=['responded_at'])

    new_status = Application.Status.ACCEPTED if accept else Application.Status.REJECTED
    note = 'Offer accepted by student.' if accept else 'Offer declined by student.'
    return transition_application(application, new_status, user, note=note)
