"""
ASGI config for beauty_salon project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

# وارد کردن تابعی که برنامه ASGI جنگو را می‌سازد
from django.core.asgi import get_asgi_application

# تنظیم مسیر فایل تنظیمات پروژه (settings.py) به عنوان یک متغیر محیطی
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beauty_salon.settings')

# ساخت یک نمونه از اپلیکیشن که سرور وب از آن برای اجرای پروژه استفاده می‌کند
application = get_asgi_application()
