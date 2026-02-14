from django import template

register = template.Library()


def three_digit_to_word(n):
    yekan = ["", "یک", "دو", "سه", "چهار", "پنج", "شش", "هفت", "هشت", "نه"]
    dahgan = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"]
    dah_to_19 = ["ده", "یازده", "دوازده", "سیزده", "چهارده", "پانزده",
                 "شانزده", "هفده", "هجده", "نوزده"]
    sadgan = ["", "صد", "دویست", "سیصد", "چهارصد",
              "پانصد", "ششصد", "هفتصد", "هشتصد", "نهصد"]

    result = ""

    hundred = n // 100
    rest = n % 100

    if hundred:
        result += sadgan[hundred] + " و "

    if 10 <= rest < 20:
        result += dah_to_19[rest - 10]
    else:
        ten = rest // 10
        one = rest % 10

        if ten:
            result += dahgan[ten]
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

    if millions:
        result += three_digit_to_word(millions) + " میلیون "

    if thousands:
        result += three_digit_to_word(thousands) + " هزار "

    if hundreds:
        result += three_digit_to_word(hundreds)

    return result.strip()
