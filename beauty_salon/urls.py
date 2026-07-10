"""
URL configuration for beauty_salon project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

#مسیرهای اصلی پروژه
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # صفحات اصلی سایت (خانه، درباره ما، تماس)
    path('',include('core.urls')),

   # سیستم رزرو نوبت ( هدایت به اپ booking)
    path('booking/',include('booking.urls')),

    # سیستم وبلاگ و مقالات ( هدایت به اپ blog_app)
    path('blog/', include('blog_app.urls')),

     # سیستم نظرات و امتیازات ( هدایت به اپ reviews_app)
    path('reviews/', include('reviews_app.urls')),
    
    # معرفی خدمات سالن ( هدایت به اپ services_app)
    path('service/', include('services_app.urls', namespace='services_app')),
    
    #برای ورود و خروحج ثبت نام ( هدایت به اپ accounts + بازیابی رمز عبور)
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),

    #پنل کاربری ( هدایت به اپ panel)
    path('panel/', include('panel.urls')),

]


# دسترسی به فایل‌های آپلود شده (مدیا) در حالت (لوکال)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)