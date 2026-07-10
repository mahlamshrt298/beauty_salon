from django.apps import AppConfig


class BlogAppConfig(AppConfig):
    # تنظیم کلید اصلی (ID) خودکار برای مدل‌های این اپلیکیشن
    default_auto_field = 'django.db.models.BigAutoField'
    
    # نام رسمی اپلیکیشن برای شناسایی در پروژه (settings.py)
    name = 'blog_app'
