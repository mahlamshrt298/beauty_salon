from django.contrib import admin
from .models import  Staff, Appointment, Payment
from .models import PendingAppointment

# ثبت مدل‌های مربوط به سیستم نوبت‌دهی در پنل ادمین
admin.site.register(Staff)      #اطلاعات پرسنل و کارکنان
admin.site.register(Appointment)    #نوبت‌های رزرو شده
admin.site.register(Payment)    #اطلاعات پرداخت‌ها

#برای رزروهای نصفه‌کاره
@admin.register(PendingAppointment)
class PendingAppointmentAdmin(admin.ModelAdmin):
    #تو لیست اصلی پنل، این ستون‌ها رو نشون بده
    list_display = ("user", "step", "is_completed", "last_activity", "created_at")
    #سایدبار سمت راست واسه فیلتر کردن
    list_filter = ("is_completed", "step")
    ## باکس سرچ بالای لیست.
    search_fields = ("user__username", "user__email")
