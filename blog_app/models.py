from django.db import models
from services_app.models import Service 
from django.contrib.auth.models import User
from django.templatetags.static import static

#مدل دسته‌بندی‌های وبلاگ
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name

#مدل مقالات
class Article(models.Model):
    
    #اطلاعات پایه
    title = models.CharField(max_length=200)
    content = models.TextField()    #محتوای اصلی
    image = models.ImageField(upload_to='blog/')
    
    # دسته‌بندی مقاله
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)  # نویسنده
    created_at = models.DateTimeField(auto_now_add=True)  # تاریخ ایجاد
    updated_at = models.DateTimeField(auto_now=True)      # تاریخ بروزرسانی
    
    # لینک کردن مقاله به یک سرویس خاص 
    for_reserve = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="خدمت مرتبط برای رزرو")

    #محتوای تکمیلی و سئو
    
    #برای نکات کلیدی
    Key_points = models.TextField(null=True, blank=True)

    # برچسب‌ها برای جستجو و مقالات مرتبط
    tags = models.CharField(max_length=500, blank=True, verbose_name="برچسب‌ها")

    #وضعیت و آمار
    show_on_home = models.BooleanField(
        default=False,
        verbose_name="نمایش در صفحه اصلی"
    )

    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name="تعداد بازدید"
    )

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return static('images/blog.jpg')

    def __str__(self):
        return self.title


        