from django.contrib import admin
from .models import SalonSettings
from .models import Package
# Register your models here.
#ثبت مدل تنظیمات سالن
admin.site.register(SalonSettings)

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    # فیلدهای نمایش در لیست
    list_display = ['title', 'discounted_price', 'is_active', 'is_limited_time']
    list_filter = ['is_active', 'is_limited_time']
    # فیلدهای قابل جستجو
    search_fields = ['title']
    #بل ویرایش مستقیم ا
    list_editable = ['is_active']
