from django.contrib import admin
from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'service',
        'rating',
        'short_comment',
        'status',
        'show_on_home',
        'created_at',
    )

    list_filter = ('status','show_on_home', 'created_at', 'service')
    search_fields = ('comment', 'user__username')
    ordering = ('-created_at',)
    list_editable = ('show_on_home',) 
    actions = ['approve_reviews', 'reject_reviews']
    fields = (
        'user',
        'service',
        'rating',
        'comment',
        'admin_reply',   # ← اضافه شد
        'status',
    )

    readonly_fields = ('user', 'service', 'rating', 'comment')
    
    def short_comment(self, obj):
        return obj.comment[:40]
    short_comment.short_description = 'نظر'

    def approve_reviews(self, request, queryset):
        queryset.update(status='approved')
    approve_reviews.short_description = "تأیید نظرات انتخاب‌شده"

    def reject_reviews(self, request, queryset):
        queryset.update(status='rejected')
    reject_reviews.short_description = "رد نظرات انتخاب‌شده"
