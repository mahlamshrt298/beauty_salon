from django.contrib import admin

# Register your models here.
# blog/admin.py
from .models import Category, Article

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'author', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['title', 'content','key_points']
    date_hierarchy = 'created_at'
   # fields = ['title', 'content', 'image', 'category', 'author', 'key_points', 'tags', 'for_reserve']
   # fields = ['title', 'content', 'image', 'category', 'author', 'key_points', 'for_reserve']  # ← اضافه شده