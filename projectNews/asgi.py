"""
ASGI config for projectNews project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projectNews.settings')
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
app = application
