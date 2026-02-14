from datetime import date

def calculate_age(birthday):
    if not birthday:
        return None

    today = date.today()
    return today.year - birthday.year - (
        (today.month, today.day) < (birthday.month, birthday.day)
    )
