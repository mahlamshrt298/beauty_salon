from django import template
from core.models import SalonSettings

register = template.Library()

"""
    دریافت اطلاعات فوتر از تنظیمات سالن
    در صورت عدم وجود، مقادیر پیش‌فرض برمی‌گرداند
"""

@register.simple_tag
def get_salon_footer_info():
    
    try:
        # فعلاً فرض بر اینه که فقط یه رکورد تنظیمات داریم، پس همون اولی رو می‌گیریم
        settings = SalonSettings.objects.first()
        if settings:
            return {
                'address': settings.address or "تهران",
                'phone': settings.phone or "02112345678",
                'phone_display': settings.phone or "۰۲۱-۱۲۳۴۵۶۷۸",
                'whatsapp': settings.whatsapp or "989123456789", 
                'open_time': settings.open_time.strftime('%H:%M') if settings.open_time else "09:00",
                'close_time': settings.close_time.strftime('%H:%M') if settings.close_time else "20:00",
                'instagram': settings.instagram or "saloon_nora",
            }
        
    except Exception:
        pass
    
    # مقادیر پیش‌فرض در صورت خطا یا عدم وجود تنظیمات
    return {
        'address': "تهران",
        'phone': "02112345678",
        'phone_display': "۰۲۱-۱۲۳۴۵۶۷۸",
        'open_time': "09:00",
        'close_time': "20:00",
        'instagram': "saloon_nora",
        'whatsapp': "989123456789",
    }