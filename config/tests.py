import json
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User


class InstallableWebAppTests(TestCase):
    def test_service_worker_is_served_from_the_site_root(self):
        self.assertEqual(reverse('service_worker'), '/sw.js')
        response = self.client.get(reverse('service_worker'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('javascript', response['Content-Type'])
        self.assertEqual(response['Service-Worker-Allowed'], '/')
        self.assertContains(response, 'CACHE_VERSION')

    def test_service_worker_is_not_cached_by_browsers(self):
        response = self.client.get('/sw.js')
        self.assertIn('no-cache', response['Cache-Control'])

    def test_offline_page_renders_without_external_assets(self):
        response = self.client.get(reverse('offline'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You are offline')
        self.assertNotContains(response, 'cdn.jsdelivr.net')

    def test_manifest_is_valid(self):
        path = finders.find('manifest.json')
        self.assertIsNotNone(path)
        manifest = json.loads(Path(path).read_text(encoding='utf-8'))

        self.assertEqual(manifest['scope'], '/')
        self.assertEqual(manifest['display'], 'standalone')
        self.assertTrue(manifest['name'])
        self.assertTrue(manifest['short_name'])
        self.assertLessEqual(len(manifest['short_name']), 12)

        sizes = {icon['sizes'] for icon in manifest['icons']}
        self.assertIn('192x192', sizes)
        self.assertIn('512x512', sizes)
        self.assertTrue(
            any(icon.get('purpose') == 'maskable' for icon in manifest['icons'])
        )

    def test_every_manifest_icon_file_exists(self):
        manifest = json.loads(
            (Path(settings.BASE_DIR) / 'static' / 'manifest.json').read_text(
                encoding='utf-8'
            )
        )
        for icon in manifest['icons']:
            relative = icon['src'].removeprefix(settings.STATIC_URL)
            self.assertIsNotNone(finders.find(relative), icon['src'])

    def test_pages_advertise_the_installable_app(self):
        response = self.client.get(reverse('dashboard:home'))
        self.assertContains(response, 'rel="manifest"')
        self.assertContains(response, 'apple-touch-icon')
        self.assertContains(response, 'name="theme-color"')
        self.assertContains(response, 'viewport-fit=cover')
        self.assertContains(response, 'js/pwa.js')


class CsrfProtectionTests(TestCase):
    """Mobile browsers are the usual source of CSRF 403s, so keep the flow
    working and make any failure explain itself."""

    def test_login_page_sets_a_csrf_cookie(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertIn('csrftoken', response.cookies)

    def test_register_page_sets_a_csrf_cookie(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertIn('csrftoken', response.cookies)

    def test_post_without_csrf_token_renders_a_helpful_page(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            reverse('accounts:login'),
            {'username': 'someone@example.com', 'password': 'wrong-password'},
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'We could not verify that form', status_code=403)
        self.assertContains(response, 'Try again', status_code=403)
        self.assertContains(response, 'Technical details', status_code=403)

    def test_login_works_when_the_csrf_cookie_is_sent(self):
        client = Client(enforce_csrf_checks=True)
        page = client.get(reverse('accounts:login'))
        token = page.cookies['csrftoken'].value
        response = client.post(
            reverse('accounts:login'),
            {
                'csrfmiddlewaretoken': token,
                'username': 'missing@example.com',
                'password': 'wrong-password',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Log in')

    def test_registration_works_when_the_csrf_cookie_is_sent(self):
        client = Client(enforce_csrf_checks=True)
        page = client.get(reverse('accounts:register'))
        token = page.cookies['csrftoken'].value
        response = client.post(
            reverse('accounts:register'),
            {
                'csrfmiddlewaretoken': token,
                'first_name': 'Nia',
                'last_name': 'Reyes',
                'email': 'nia@example.com',
                'role': 'student',
                'password1': 'strong-pass-4821',
                'password2': 'strong-pass-4821',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:home'))

    def test_trusted_origins_cover_accepted_hosts(self):
        for host in settings.ALLOWED_HOSTS:
            if host in ('localhost', '127.0.0.1', 'testserver'):
                continue
            if host.startswith('.') or host == '*':
                continue
            self.assertIn(f'https://{host}', settings.CSRF_TRUSTED_ORIGINS)

    def test_login_and_register_pages_are_never_cached(self):
        for name in ('accounts:login', 'accounts:register'):
            response = self.client.get(reverse(name))
            cache_control = response['Cache-Control']
            self.assertIn('no-store', cache_control, name)
            self.assertIn('no-cache', cache_control, name)

    def test_diagnostics_page_renders(self):
        response = self.client.get(reverse('diagnostics'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Connection check')
        self.assertContains(response, 'Test a form submission')

    def test_diagnostics_form_submission_is_accepted_with_a_token(self):
        client = Client(enforce_csrf_checks=True)
        page = client.get(reverse('diagnostics'))
        token = page.cookies['csrftoken'].value
        response = client.post(reverse('diagnostics'), {'csrfmiddlewaretoken': token})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'was accepted')


class WebViewCsrfTests(TestCase):
    """Installed apps and in-app browsers send odd Origin/Referer headers.

    The request must still succeed when the CSRF token is valid, and must still
    be rejected when it is missing or comes from another site.
    """

    def _client(self):
        return Client(enforce_csrf_checks=True)

    # Production is HTTPS, where Django's Origin/Referer checks are enforced.
    HTTPS = {'wsgi.url_scheme': 'https'}

    def _post(self, client, token, **extra):
        return client.post(
            reverse('accounts:login'),
            {
                'csrfmiddlewaretoken': token,
                'username': 'nobody@example.com',
                'password': 'wrong-password',
            },
            **self.HTTPS,
            **extra,
        )

    def _token(self, client):
        page = client.get(reverse('accounts:login'), **self.HTTPS)
        return page.cookies['csrftoken'].value

    def test_null_origin_is_accepted_with_a_valid_token(self):
        client = self._client()
        response = self._post(
            client,
            self._token(client),
            HTTP_ORIGIN='null',
            HTTP_REFERER='https://testserver/accounts/login/',
        )
        self.assertEqual(response.status_code, 200)

    def test_missing_origin_and_referer_are_accepted_with_a_valid_token(self):
        client = self._client()
        response = self._post(client, self._token(client))
        self.assertEqual(response.status_code, 200)

    def test_foreign_origin_is_still_rejected(self):
        client = self._client()
        response = self._post(
            client,
            self._token(client),
            HTTP_ORIGIN='https://evil.example',
        )
        self.assertEqual(response.status_code, 403)

    def test_foreign_referer_is_still_rejected(self):
        client = self._client()
        response = self._post(
            client,
            self._token(client),
            HTTP_REFERER='https://evil.example/page',
        )
        self.assertEqual(response.status_code, 403)

    def test_null_origin_without_a_token_is_still_rejected(self):
        client = self._client()
        response = client.post(
            reverse('accounts:login'),
            {'username': 'nobody@example.com', 'password': 'wrong-password'},
            HTTP_ORIGIN='null',
            **self.HTTPS,
        )
        self.assertEqual(response.status_code, 403)


class AdminPortalTests(TestCase):
    """The admin portal is hidden and only reachable by signed-in staff."""

    def setUp(self):
        self.staff = User.objects.create_superuser(
            email='admin@test.com',
            password='admin-pass-4821',
            first_name='Portal',
            last_name='Admin',
        )
        self.student = User.objects.create_user(
            email='student@test.com',
            password='student-pass-4821',
            first_name='Sam',
            last_name='Student',
            role=User.Role.STUDENT,
        )

    def test_admin_path_defaults_to_admin(self):
        self.assertEqual(settings.ADMIN_PATH, '/admin/')

    def test_anonymous_gets_404_for_the_admin_index(self):
        response = self.client.get(settings.ADMIN_PATH)
        self.assertEqual(response.status_code, 404)

    def test_anonymous_gets_404_for_the_admin_login_page(self):
        response = self.client.get(settings.ADMIN_PATH + 'login/')
        self.assertEqual(response.status_code, 404)

    def test_admin_path_without_a_trailing_slash_is_hidden_too(self):
        response = self.client.get(settings.ADMIN_PATH.rstrip('/'), follow=True)
        self.assertEqual(response.status_code, 404)

    def test_signed_in_non_staff_is_redirected_to_the_dashboard(self):
        self.client.force_login(self.student)
        response = self.client.get(settings.ADMIN_PATH)
        self.assertRedirects(response, reverse('dashboard:home'))

    def test_signed_in_non_staff_does_not_reach_the_admin_login(self):
        self.client.force_login(self.student)
        response = self.client.get(settings.ADMIN_PATH + 'login/')
        self.assertRedirects(response, reverse('dashboard:home'))

    def test_staff_can_open_the_admin(self):
        self.client.force_login(self.staff)
        response = self.client.get(settings.ADMIN_PATH)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Site administration')

    def test_staff_sign_in_through_the_portal_then_reach_the_admin(self):
        response = self.client.post(
            reverse('accounts:login'),
            {'username': self.staff.email, 'password': 'admin-pass-4821'},
        )
        self.assertRedirects(response, reverse('dashboard:home'))
        self.assertEqual(self.client.get(settings.ADMIN_PATH).status_code, 200)
