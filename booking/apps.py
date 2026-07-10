from django.apps import AppConfig

# کلاس تنظیمات اصلی اپلیکیشن رزرو 
class AppointmentReservationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    # اسم دقیق اپلیکیشن که جنگو باهاش این اپ رو می‌شناسه و تو INSTALLED_APPS هم همینو استفاده می‌کنیم
    name = 'booking'

    # این متد زمانی اجرا میشه که جنگو استارت خورده و اپلیکیشن کاملاً لود شده
    def ready(self):
        # ایمپورت کردن فایل سیگنال‌ها
        import booking.signals

