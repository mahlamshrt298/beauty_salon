from django.core.cache import cache
from .models import Notification

def unread_notifications(request):
    # اگه کاربر لاگین نکرده بود الکی دیتابیس رو درگیر نمی‌کنیم
    if not request.user.is_authenticated:
        return {'unread_notifications_count': 0, 'latest_notifications': []}

    cache_key_count = f'notif_count_{request.user.id}'
    cache_key_latest = f'notif_latest_{request.user.id}'

    # اول چک می‌کنیم ببینیم دیتا از قبل تو کش هست یا نه
    count = cache.get(cache_key_count)
    latest = cache.get(cache_key_latest)

    if count is None:
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        cache.set(cache_key_count, count, 60)

    #گرفتن ۵ تا نوتیفیکیشن آخر یوزر
    if latest is None:
        latest = list(Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5])
        cache.set(cache_key_latest, latest, 60)

    return {
        'unread_notifications_count': count,
        'latest_notifications': latest
    }
