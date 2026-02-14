from django.contrib import admin
from .models import  Staff, Appointment, Payment

# ثبت مدل‌های مربوط به سیستم نوبت‌دهی در پنل ادمین
admin.site.register(Staff)      #اطلاعات پرسنل و کارکنان
admin.site.register(Appointment)    #نوبت‌های رزرو شده
admin.site.register(Payment)    #اطلاعات پرداخت‌ها

from .models import PendingAppointment

@admin.register(PendingAppointment)
class PendingAppointmentAdmin(admin.ModelAdmin):
    list_display = ("user", "step", "is_completed", "last_activity", "created_at")
    list_filter = ("is_completed", "step")
    search_fields = ("user__username", "user__email")
