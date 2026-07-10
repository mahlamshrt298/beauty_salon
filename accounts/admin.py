from django.contrib import admin
from .models import Notification , Profile

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "type",
        "channel",
        "status",
        "created_at",
        "sent_at",
    )
    #فیلترهای سایدبار
    list_filter = ("type", "channel", "status")
    
    search_fields = ("user__username", "message")

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')