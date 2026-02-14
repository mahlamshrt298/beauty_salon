from django.contrib.auth.models import User
from core.utils.birthday import handle_birthday_logic

def daily_birthday_check():
    for user in User.objects.all():
        if hasattr(user, "profile"):
            handle_birthday_logic(user)
