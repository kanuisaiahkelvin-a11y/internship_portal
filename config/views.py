import logging

from django.conf import settings
from django.shortcuts import render
from django.template.response import TemplateResponse

logger = logging.getLogger('internlink.security')


def service_worker(request):
    """Serve the service worker from the site root.

    A worker served from /static/ could only control /static/. Serving it at
    /sw.js with ``Service-Worker-Allowed: /`` lets it control the whole site.
    """
    response = TemplateResponse(
        request,
        'pwa/sw.js',
        content_type='application/javascript; charset=utf-8',
    )
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response


def _csrf_hint(reason):
    """Turn Django's technical CSRF reason into an actionable bucket."""
    text = (reason or '').lower()
    if 'cookie not set' in text:
        return 'cookies'
    if 'token incorrect' in text:
        return 'stale'
    if 'origin checking failed' in text or 'referer checking failed' in text:
        return 'origin'
    if 'token missing' in text:
        return 'cookies'
    return 'generic'


def csrf_failure(request, reason=''):
    """Replace Django's bare "403 Forbidden" with a fix-it page.

    Mobile browsers are the usual source of these failures: in-app browsers
    (Messenger, Instagram, Facebook, Gmail) and private tabs drop cookies, and
    some webviews send a Referer from the host app instead of this site.
    """
    hint = _csrf_hint(reason)
    logger.warning(
        'CSRF failure on %s %s: %s | hint=%s secure=%s host=%s origin=%s '
        'referer=%s cookies=%s ua=%s',
        request.method,
        request.path,
        reason,
        hint,
        request.is_secure(),
        request.get_host(),
        request.META.get('HTTP_ORIGIN', 'none'),
        request.META.get('HTTP_REFERER', 'none')[:120],
        ','.join(sorted(request.COOKIES)) or 'none',
        request.META.get('HTTP_USER_AGENT', 'unknown')[:160],
    )

    retry_url = request.path
    if request.method != 'POST' or 'logout' in request.path:
        retry_url = '/'

    context = {
        'reason': reason,
        'hint': hint,
        'retry_url': retry_url,
    }
    return render(request, '403_csrf.html', context, status=403)


def diagnostics(request):
    """Report what the server actually received from this browser/app.

    Opened from an installed home-screen app, this shows whether the browser is
    sending cookies at all — which is what breaks logins inside a PWA whose
    storage was never initialised.
    """
    cookie_names = sorted(request.COOKIES)
    post_result = None
    if request.method == 'POST':
        post_result = 'accepted'
        logger.info(
            'Diagnostics POST accepted from %s (cookies=%s)',
            request.META.get('HTTP_USER_AGENT', 'unknown')[:120],
            ','.join(cookie_names) or 'none',
        )

    context = {
        'post_result': post_result,
        'host': request.get_host(),
        'scheme': request.scheme,
        'is_secure': request.is_secure(),
        'csrf_cookie_present': 'csrftoken' in request.COOKIES,
        'session_cookie_present': settings.SESSION_COOKIE_NAME in request.COOKIES,
        'cookie_names': ', '.join(cookie_names) or 'none',
        'origin': request.META.get('HTTP_ORIGIN', 'not sent'),
        'referer': request.META.get('HTTP_REFERER', 'not sent'),
        'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown'),
        'secure_cookies_required': settings.CSRF_COOKIE_SECURE,
        'debug': settings.DEBUG,
    }
    return render(request, 'support/diagnostics.html', context)
