from django import template
from core.models import SalonSettings

register = template.Library()

@register.simple_tag
def get_salon_footer_info():
    """
    دریافت اطلاعات فوتر از تنظیمات سالن
    در صورت عدم وجود، مقادیر پیش‌فرض برمی‌گرداند
    """
    try:
        settings = SalonSettings.objects.first()
        if settings:
            return {
                'address': settings.address or "تهران، میدان ولیعصر، خیابان نورا، پلاک ۱۲",
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
        'address': "تهران، میدان ولیعصر، خیابان نورا، پلاک ۱۲",
        'phone': "02112345678",
        'phone_display': "۰۲۱-۱۲۳۴۵۶۷۸",
        'open_time': "09:00",
        'close_time': "20:00",
        'instagram': "saloon_nora",
        'whatsapp': "989123456789",
    }