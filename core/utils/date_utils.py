from datetime import date

#محاسبه دقیق سن کاربر با در نظر گرفتن ماه و روز.
def calculate_age(birthday):
    #اگر کاربر تاریخ تولد وارد نکرده بود، none برگردون
    if not birthday:
        return None

    today = date.today()
    # اگر تولد رو رد نکرده باشیم، یکی کم میشه تا سن دقیق در بیاد
    return today.year - birthday.year - (
        (today.month, today.day) < (birthday.month, birthday.day)
    )
