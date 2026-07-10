from . import views
from django.urls import path,include

#مسیر های اصلی
urlpatterns = [

    #صفحه اصلی
    path('', views.home,name='home'),
    #صفحه تماس با ما
    path('contact/', views.contact,name='contact'),
    
    #صفحه درباره ما
    path('about/', views.about,name='about'),
    
    #مربوط به تایید پرداخت پکیج‌های تخفیفی
    path(
        'package/<int:package_id>/payment/',
        views.package_payment_confirm,
        name='package_payment_confirm'
    ),

]