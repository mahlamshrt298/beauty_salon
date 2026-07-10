# این ماژول برای ساخت تگ‌ها و فیلترهای سفارشی ضروری است.
from django import template

register = template.Library()

@register.filter
def to_range(start, end):
    return range(start, end + 1)
