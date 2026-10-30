import logging

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
        'CSRF failure on %s %s: %s | hint=%s secure=%s cookie_sent=%s ua=%s',
        request.method,
        request.path,
        reason,
        hint,
        request.is_secure(),
        'csrftoken' in request.COOKIES,
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
