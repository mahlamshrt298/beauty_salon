from django.contrib.auth.models import User
from core.utils.birthday import handle_birthday_logic

#کارش اینه که لیست یوزرها رو شخم بزنه و چک کنه تولد کی نزدیکه
def daily_birthday_check():
    for user in User.objects.all():
        if hasattr(user, "profile"):
            #پاس دادن آبجکت یوزر به فانکشن اصلی برای محاسبه روزها و تولید کد تخفیف
            handle_birthday_logic(user)

            