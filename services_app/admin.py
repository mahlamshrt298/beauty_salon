from django.contrib import admin
from .models import Category, Subcategory, Service, ServiceImage , PopularService
# جلوگیری از خطا در صورت ثبت قبلی
try:
    admin.site.unregister(Service)
except admin.sites.NotRegistered:
    pass
try:
    admin.site.unregister(Category)
except admin.sites.NotRegistered:
    pass
try:
    admin.site.unregister(Subcategory)
except admin.sites.NotRegistered:
    pass

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

# --- اضافه کردن Admin برای Subcategory ---
@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug']
    list_filter = ['category']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'category__name'] # جستجو بر اساس نام زیردسته یا دسته اصلی


# --- اضافه کردن Inline برای ServiceImage ---
class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 1  # تعداد فرم‌های اضافی برای اضافه کردن عکس
    fields = ['image', 'alt_text']  # فیلدهایی که در ادمین نمایش داده می‌شوند
    verbose_name = "عکس مرتبط"
    verbose_name_plural = "عکس‌های مرتبط"

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'subcategory', 'price', 'duration_minutes', 'is_active'] # ✅ subcategory اضافه شد
    list_filter = ['category', 'subcategory', 'is_active'] # ✅ subcategory اضافه شد
    search_fields = ['name', 'category__name', 'subcategory__name'] # ✅ جستجو بر اساس نام زیردسته
    list_editable = ['price', 'is_active']
    inlines = [ServiceImageInline] 
    # اگر می‌خواهی در لیست سرویس‌ها زیردسته را هم ویرایش کنی، این خط را اضافه کن:
    # list_editable = ['price', 'is_active', 'subcategory']

@admin.register(PopularService)
class PopularServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_active', 'order')
    list_editable = ('is_active', 'order')
    search_fields = ('title',)