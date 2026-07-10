from booking import views
from django.urls import path

urlpatterns = [
    # صفحات اصلی مراحل رزرو
    
    # صفحه اول: لیست سرویس‌ها 
    path('reserve/', views.reserve,name='reserve'),
    
    #صفحه دوم: تقویم و انتخاب روز/ساعت 
    path('select-date/<int:service_id>/', views.select_date, name='select_date'),
    
    #هندل کردن عوض کردن ماه و سال در تقویم
    path('select-date/<int:service_id>/<int:year>/<int:month>/', views.select_date, name='select_date_with_month'),
    
    #تقویم برای رزرو پکیج‌ها
    path("select-date/package/<int:package_id>/", views.select_date_from_package, name="select_date_from_package"),

    # مرحله سوم: فرم اطلاعات شخصی کاربر
    path('contact-info/', views.contact_info, name='contact_info'),
    
    # مرحله چهارم: تایید نهایی برای رفتن به درگاه پرداخت
    path('payment-confirm/', views.payment_confirm, name='payment_confirm'),
    
    # صفحه نهایی: نمایش رسید رزرو به همراه کد پیگیری
    path('confirmation/<str:tracking_code>/', views.confirmation, name='confirmation'),

    # درخواست‌های ایجکس (AJAX) و توابع کمکی

    # گرفتن تایم‌های خالی یک روز مشخص برای آپدیت کردن تقویم
    path('get-available-times/', views.get_available_times, name='get_available_times'),
    
    # واکشی لیست پرسنلِ آزاد برای یک سرویس و زمان خاص
    path(
        "ajax/get-available-staff/",
        views.get_available_staff_ajax,
        name="get_available_staff"
    ),

]