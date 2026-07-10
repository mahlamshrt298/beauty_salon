"""
WSGI config for beauty_salon project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# معرفی فایل تنظیمات پروژه به سرور (برای پیدا کردن settings.py)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beauty_salon.settings')

# ساخت شیء WSGI برای تحویل درخواست‌های وب به جنگو
application = get_wsgi_application()
