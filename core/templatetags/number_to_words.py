from django import template

register = template.Library()

#یه عدد ۳ رقمی میگیره و حروف فارسیش رو برمیگردونه
def three_digit_to_word(n):
    yekan = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه"]
    dahgan = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]
    
    #اعداد ۱۰ تا ۱۹ 
    dah_to_19 = ["ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده",
                 "شانزده", "هفده", "هجده", "نوزده"]
    sadgan = ["", "صد", "دویست", "سیصد", "چهارصد",
              "پانصد", "ششصد", "هفتصد", "هشتصد", "نهصد"]

    result = ""

    # جدا کردن صدگان و بقیه عدد (دو رقم آخر) با تقسیم صحیح و باقی‌مانده
    hundred = n // 100
    rest = n % 100

    if hundred:
        # اگه صدگان داشتیم کلمه مربوطه رو میذاریم و یه 'و' بهش میچسبونیم
        result += sadgan[hundred] + " و "

    # هندل کردن استثنای بین ۱۰ تا ۱۹
    if 10 <= rest < 20:
        result += dah_to_19[rest - 10]
    else:
        # اگه کمتر از ۱۰ یا بیشتر مساوی ۲۰ بود، دهگان و یکان رو عادی جدا حساب میکنیم
        ten = rest // 10
        one = rest % 10

        if ten:
            result += dahgan[ten]
            #اگه یکان هم داشتیم بعد از دهگان یه 'و' میخوایم
            if one:
                result += " و "

        if one:
            result += yekan[one]

    return result.strip(" و")


@register.filter
def persian_words(value):
    try:
        num = int(value)
    except:
        return ""

    if num == 0:
        return "صفر"

    result = ""

    millions = num // 1_000_000
    thousands = (num % 1_000_000) // 1000
    hundreds = num % 1000

    # هر بلوک ۳ رقمی رو میدیم به تابع بالاییمون و پسوندش رو بهش میچسبونیم

    if millions:
        result += three_digit_to_word(millions) + " میلیون "

    if thousands:
        # چک میکنیم اگه هزارگان داریم بنویسه هزار. 
        result += three_digit_to_word(thousands) + " هزار "

    if hundreds:
        result += three_digit_to_word(hundreds)

    return result.strip()
