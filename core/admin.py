from django.contrib import admin
from .models import SalonSettings
from .models import Package

#ثبت مدل تنظیمات سالن
admin.site.register(SalonSettings)

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    # ستون‌هایی که تو صفحه اصلی لیست پکیج‌ها نشون داده میشن.
    list_display = ['title', 'discounted_price', 'is_active', 'is_limited_time']
    #فیلترهای سایدبار
    list_filter = ['is_active', 'is_limited_time']
    # فیلدهای قابل جستجو
    search_fields = ['title']
    #بل ویرایش مستقیم ا
    list_editable = ['is_active']
