from django.template.response import TemplateResponse


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
