import json
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse


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
