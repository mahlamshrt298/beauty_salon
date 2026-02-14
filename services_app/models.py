from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static

# Create your models here.

#دسته‌بندی‌های خدمات
class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("نام دسته"))
    slug = models.SlugField(unique=True, blank=True, verbose_name=_("اسلاگ"))    # اسلاگ برای URLهای SEO-friendly

    class Meta:
        verbose_name = _("دسته‌بندی")
        verbose_name_plural = _("دسته‌بندی‌ها")

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while self.__class__.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.name

# --- اضافه کردن مدل Subcategory ---
class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories', verbose_name=_("دسته اصلی"))
    name = models.CharField(max_length=100, verbose_name=_("نام زیردسته"))
    slug = models.SlugField(unique=True, blank=True, verbose_name=_("اسلاگ"))
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))

    class Meta:
        verbose_name = _("زیردسته")
        verbose_name_plural = _("زیردسته‌ها")
        # اینجا یک قاعده برای مرتب‌سازی اضافه می‌کنیم
        ordering = ['category', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1

            while self.__class__.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.category.name} - {self.name}"


# 🧍‍♀️ مدل خدمات سالن
class Service(models.Model):
    image = models.ImageField(upload_to='services/', blank=True, null=True, verbose_name="عکس اصلی")
    name = models.CharField(max_length=200, verbose_name=_("نام خدمت"))
    # توضیحات کامل خدمت
    description = models.TextField(blank=True, null=True,verbose_name=_("توضیحات"))
    # مدت زمان انجام خدمت 
    duration_minutes = models.IntegerField(default=30,verbose_name=_("مدت زمان (دقیقه)"))
    price = models.PositiveIntegerField(verbose_name=_("قیمت (تومان)"))
    # وضعیت فعال/غیرفعال بودن خدمت
    is_active = models.BooleanField(default=True,verbose_name=_("فعال است"))
    subcategory = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='services', verbose_name=_("زیردسته"))
    slug = models.SlugField(unique=True, blank=True, verbose_name=_("اسلاگ"))
    # دسته‌بندی مرتبط
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='services', verbose_name=_("دسته اصلی"))
    
    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return static('images/service.png')

    class Meta:
        verbose_name = _("خدمت")
        verbose_name_plural = _("خدمات")

    def approved_reviews(self):
        """برگرداندن نظرات تأیید شده مرتبط با این خدمت"""
        return self.reviews.filter(service=self, status='approved').order_by('-created_at')
    
    def get_related_images(self):
        """برگرداندن عکس‌های مرتبط با این خدمت"""
        return self.related_images.all()

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            while self.__class__.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
#  مدل عکس‌های مرتبط با خدمت
class ServiceImage(models.Model):
    #برای نمایش گالری تصاویر در صفحه جزئیات خدمت
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='related_images')
    image = models.ImageField(upload_to='service_images/')
    
    # متن جایگزین برای SEO
    alt_text = models.CharField(max_length=200, blank=True, null=True)
    
    # تاریخ آپلود
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.service.name} - Image {self.id}"


class PopularService(models.Model):
    title = models.CharField(max_length=100, verbose_name="عنوان")
    description = models.TextField(verbose_name="توضیحات")
    image = models.ImageField(upload_to='popular_services/', verbose_name="تصویر")
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="popular_services",
        
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال باشد؟")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")

    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return static('images/popularservice.jpg')

    class Meta:
        ordering = ['order']
        verbose_name = "خدمت پرطرفدار"
        verbose_name_plural = "خدمات پرطرفدار"

    def __str__(self):
        if self.category:
            return f"{self.title} ({self.category.name})"
        return f"{self.title} (بدون دسته‌بندی)"

