from django.contrib import admin

from .models import Category, Article

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    # ستون‌هایی که در جدول لیست مقالات در پنل ادمین نمایش داده می‌شوند
    list_display = ['title', 'category', 'author', 'created_at']
    
    #اضافه کردن پنل فیلتر
    list_filter = ['category', 'created_at']
    
    #اضافه کردن باکس جستجو در بالای لیست
    search_fields = ['title', 'content','key_points']
    
    # اضافه کردن نوار ناوبری تاریخ
    date_hierarchy = 'created_at'
