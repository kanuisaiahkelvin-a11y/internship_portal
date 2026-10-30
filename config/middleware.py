"""Middleware that makes Django's CSRF checks work inside mobile webviews.

Installed home-screen apps and in-app browsers (Messenger, Instagram, WhatsApp,
Gmail) are inconsistent about the ``Origin`` and ``Referer`` headers. Some send
``Origin: null``, some send neither. Django then refuses a genuine same-site
form post with "Origin checking failed" or "Referer checking failed".

This middleware restores the headers Django expects, but only for requests that
really came from this site: an absent or ``null`` origin is replaced with the
request's own origin, and a ``Referer`` pointing at another host still blocks
the request. The CSRF token and cookie checks are untouched, so a request
without a valid token is still rejected.
"""

from urllib.parse import urlsplit

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect

SAFE_METHODS = frozenset({'GET', 'HEAD', 'OPTIONS', 'TRACE'})


def _hostname(value):
    """Return the hostname of a URL, or of a bare ``host:port`` value."""
    if not value:
        return None
    if '//' not in value:
        value = f'//{value}'
    try:
        return (urlsplit(value).hostname or '').lower() or None
    except ValueError:
        return None


class NormalizeCsrfHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in SAFE_METHODS:
            self._repair_origin(request)
        return self.get_response(request)

    @staticmethod
    def _repair_origin(request):
        origin = request.META.get('HTTP_ORIGIN')
        if origin not in (None, '', 'null'):
            return

        try:
            host = request.get_host()
        except Exception:  # DisallowedHost — let Django reject it normally.
            return

        # A Referer from another site means this is not our own page.
        referer = request.META.get('HTTP_REFERER')
        if referer and _hostname(referer) != _hostname(host):
            return

        own_origin = f"{'https' if request.is_secure() else 'http'}://{host}"
        request.META['HTTP_ORIGIN'] = own_origin
        if not referer:
            request.META['HTTP_REFERER'] = f'{own_origin}/'


class AdminPortalMiddleware:
    """Hide the Django admin behind a signed-in staff check.

    The admin is never advertised: an anonymous request to the admin path gets
    a 404, exactly as if nothing were mounted there, so scanners and casual
    visitors cannot find it. A signed-in user without staff access is sent back
    to their dashboard with an explanation. Staff pass through to the admin and
    its usual permission checks.

    Staff sign in through the regular portal login (``/accounts/login/``), not
    the admin login page, because the admin login is hidden along with the rest.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        admin_path = settings.ADMIN_PATH
        bare_path = admin_path.rstrip('/')
        if request.path_info == bare_path or request.path_info.startswith(
            admin_path
        ):
            user = getattr(request, 'user', None)
            if user is None or not user.is_authenticated:
                raise Http404('Not found')
            if not user.is_staff:
                messages.error(
                    request,
                    'The admin portal is restricted to administrators.',
                )
                return redirect('dashboard:home')
        return self.get_response(request)
