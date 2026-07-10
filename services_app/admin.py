from django.contrib import admin
from .models import Category, Subcategory, Service, ServiceImage , PopularService

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug']
    list_filter = ['category']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'category__name'] 

#میتونه با این چندتا عکس رو با هم آپلود کنه
class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 1  # تعداد فرم‌های اضافی برای اضافه کردن عکس
    fields = ['image', 'alt_text']  
    verbose_name = "عکس مرتبط"
    verbose_name_plural = "عکس‌های مرتبط"

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'subcategory', 'price', 'duration_minutes', 'is_active'] 
    list_filter = ['category', 'subcategory', 'is_active'] 
    search_fields = ['name', 'category__name', 'subcategory__name'] 
    list_editable = ['price', 'is_active']
    #بخش آپلود چندگانه عکس
    inlines = [ServiceImageInline] 
   
@admin.register(PopularService)
class PopularServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_active', 'order')
    #ترتیب نمایش و فعال و غیرفعال بودن
    list_editable = ('is_active', 'order')
    search_fields = ('title',)