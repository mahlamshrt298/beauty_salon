from core.models import SalonSettings
from .models import Package  #  Package توی core هست
from services_app.models import PopularService
from blog_app.models import Article, Category
from reviews_app.models import Review
from booking.models import Staff 
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render,redirect ,get_object_or_404
from booking.models import PackagePayment
from core.models import PackageBooking
from django.contrib.auth.decorators import login_required, user_passes_test
from core.models import SalonSettings

def about(request):
    # ✅ دریافت پرسنل‌های فعال و قابل نمایش در صفحه درباره ما
    staff_members = Staff.objects.filter(
        is_active=True,
        status='active',
        show_in_about_page=True
    ).order_by('full_name')  # مرتب‌سازی بر اساس نام
    
    # ✅ اضافه کردن دو مقاله آخر (همانند صفحه خانه)
    latest_articles = Article.objects.order_by('-created_at')[:2]  # ← این خط جدید

    #نمایش صفحه درباره ما
    context = {
        'active_page': 'about',
         'staff_members': staff_members, 
         'latest_articles': latest_articles,} # ← اینجا مشخص می‌کنه که صفحه فعلی "about" هست
    return render(request,'about.html',context)  

def contact(request):
    # نمایش صفحه تماس با ما
    context = {
        'active_page': 'contact',}  # ← اینجا مشخص می‌کنه که صفحه فعلی "contact" هست
    return render(request,'contact.html',context)

def home(request):
    MAX_ITEMS = 4
    popular_services = PopularService.objects.filter(is_active=True)[:4]
    latest_articles = Article.objects.order_by('-created_at')[:2]
    # متن صفحه خانه
    # اول: مقاله‌هایی که دستی انتخاب شدند
   # 1️⃣ مقالات انتخاب‌شده توسط منشی
    manual_articles = list(
        Article.objects
        .filter(show_on_home=True)
        .order_by('-updated_at')[:MAX_ITEMS]
    )

    # 2️⃣ پر کردن با پربازدیدها
    remaining = MAX_ITEMS - len(manual_articles)

    if remaining > 0:
        extra = Article.objects.exclude(
            id__in=[a.id for a in manual_articles]
        ).order_by('-views_count')[:remaining]
    else:
        extra = []

    home_articles = manual_articles + list(extra)
    home_reviews = Review.objects.filter(
        status='approved'
    ).select_related('user', 'service').order_by('-created_at')[:3]

    print("USER:", request.user)
      # ← اینجا مشخص می‌کنه که صفحه فعلی "home" هست
    # پکیج‌های فعال
    active_packages = Package.objects.filter(is_active=True ,  show_on_homepage=True )

    # اضافه کردن زمان باقی‌مانده به هر پکیج
    for package in active_packages:
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

    try:
        salon_settings = SalonSettings.objects.first()
        if not salon_settings:
            # ایجاد مقادیر پیش‌فرض در صورت عدم وجود
            salon_settings = SalonSettings(
                address="تهران، میدان ولیعصر، خیابان نورا، پلاک ۱۲",
                phone="02112345678",
                instagram="saloon_nora",
                whatsapp="989123456789",
                open_time="09:00",
                close_time="20:00"
            )
    except Exception:
        # مقادیر پیش‌فرض کامل در صورت خطا
        salon_settings = type('obj', (object,), {
            'address': "تهران، میدان ولیعصر، خیابان نورا، پلاک ۱۲",
            'phone': "02112345678",
            'instagram': "saloon_nora",
            'whatsapp': "989123456789",
            'open_time': "09:00",
            'close_time': "20:00"
        })()
    context = {
        'active_page': 'home',
        'home_reviews': home_reviews,
        'popular_services': popular_services,
        'latest_articles': latest_articles,
        "home_articles": home_articles,
        'salon_settings': salon_settings,
        }
    context['packages'] = active_packages  # اضافه کردن پکیج‌ها به context
    return render(request, 'home.html', context)

@login_required
def package_payment_confirm(request, package_id):
    package = get_object_or_404(Package, id=package_id, is_active=True)

    if request.method == "POST":
        payment_method = request.POST.get("payment_method", "online")

        PackagePayment.objects.create(
            user=request.user,
            package=package,
            amount=package.discounted_price,
            payment_method=payment_method,
            status='success' if payment_method == 'cash' else 'pending'
        )

        # ساخت PackageBooking برای هر سرویس
        for service in package.service.all():
            PackageBooking.objects.get_or_create(
                user=request.user,
                package=package,
                service=service
            )

        request.session['package_id'] = package.id
        request.session['package_paid'] = True

        return redirect('select_date_from_package', package_id=package.id)

    return render(request, 'package_payment_confirm.html', {
        'package': package
    })
