from django.shortcuts import render ,get_object_or_404
from reviews_app.models import Review
from .models import Category, Service, Subcategory
from core.models import Package  
from datetime import timedelta
from django.utils import timezone
from django.db.models import Prefetch
from django.http import JsonResponse
import jdatetime
from services_app.models import number_to_persian_words

#تبدیل تاریخ میلادی به شمسی
def to_jalali(datetime_obj):
    if not datetime_obj:
        return ""
    jd = jdatetime.datetime.fromgregorian(datetime=datetime_obj)
    return jd.strftime('%Y/%m/%d - %H:%M')

def services_list(request):

    active_services = Service.objects.filter(is_active=True)
    
    # گرفتن دسته‌ها به همراه زیردسته‌ها و سرویس‌هاشون
    categories = Category.objects.prefetch_related(Prefetch('subcategories__services', queryset=active_services)).all()
    packages = Package.objects.filter(is_active=True , show_on_homepage=True )
    
    # تبدیل قیمت‌ها به حروف فارسی
    for package in packages:
        package.discounted_price_words = number_to_persian_words(int(package.discounted_price))
        if package.original_price:
            package.original_price_words = number_to_persian_words(int(package.original_price))
        else:
            package.original_price_words = ''

    # هندل کردن تایمر معکوس برای پکیج‌های زمان‌دار
    for package in packages:
        if package.is_limited_time and package.start_time:
            end_time = package.start_time + timedelta(days=package.duration_days)
            now = timezone.now()
            
            if now < end_time:
                remaining = end_time - now
                package.remaining_seconds = int(remaining.total_seconds())
                package.timer_active = True
            else:
                package.timer_active = False
        else:
            package.timer_active = False

    # متصل کردن تاریخ شمسی به نظرات تاییدشده‌ی هر سرویس
    for category in categories:
        for subcategory in category.subcategories.all():
            for service in subcategory.services.all():
                reviews = service.approved_reviews() 
                for review in reviews:
                    review.jalali_created_at = to_jalali(review.created_at)
        
    context = {
        'categories': categories,   
        'packages': packages,
        'active_page': 'service', 
    }
    return render(request, 'service/service.html', context)


def get_subcategories(request):
    category_id = request.GET.get('category_id')
    subcategories = Subcategory.objects.filter(category_id=category_id).values('id', 'name')
    return JsonResponse(list(subcategories), safe=False)

def get_services(request):
    subcategory_id = request.GET.get('subcategory_id')
    services = Service.objects.filter(subcategory_id=subcategory_id , is_active=True).values('id', 'name')
    return JsonResponse(list(services), safe=False)