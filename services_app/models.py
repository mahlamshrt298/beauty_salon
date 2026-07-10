from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static

#تبدیل عدد به حروف فارسی
def number_to_persian_words(number):
    ones = [
        "", "یک", "دو", "سه", "چهار", "پنج", "شش",
        "هفت", "هشت", "نه", "ده", "یازده", "دوازده",
        "سیزده", "چهارده", "پانزده", "شانزده",
        "هفده", "هجده", "نوزده"
    ]

    tens = [
        "", "", "بیست", "سی", "چهل",
        "پنجاه", "شصت", "هفتاد",
        "هشتاد", "نود"
    ]

    hundreds = [
        "", "صد", "دویست", "سیصد",
        "چهارصد", "پانصد", "ششصد",
        "هفتصد", "هشتصد", "نهصد"
    ]

    thousands = ["", "هزار", "میلیون", "میلیارد"]

    if number == 0:
        return "صفر"

    words = []

    #برای هندل کردن بلوک‌های سه رقمی
    def three_digit_to_words(n):
        n = int(n)
        result = []
        h = n // 100
        t = (n % 100) // 10
        o = n % 10

        if h:
            result.append(hundreds[h])

        if t > 1:
            result.append(tens[t])
            if o:
                result.append(ones[o])
        elif t == 1:
            result.append(ones[n % 100])        # برای اعداد بین 11 تا 19
        elif o:
            result.append(ones[o])

        return " و ".join(result)

    parts = []
    i = 0

    # این سه رقم ، سه رقم از اخرعدد به اول عدد میاد
    while number > 0:
        n = number % 1000
        if n:
            word = three_digit_to_words(n)
            if thousands[i]:
                word += f" {thousands[i]}"
            parts.append(word)
        number //= 1000
        i += 1

    #لیست رو برعکس می‌کنیم و با "و" به هم می‌چسبونیم
    return " و ".join(reversed(parts))

#دسته‌بندی‌های خدمات
class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("نام دسته"))
    slug = models.SlugField(unique=True, blank=True, verbose_name=_("اسلاگ"))    

    class Meta:
        verbose_name = _("دسته‌بندی")
        verbose_name_plural = _("دسته‌بندی‌ها")

    def save(self, *args, **kwargs):
        if not self.slug:
            #allow_unicode برای پشتیبانی از فارسی
            base_slug = slugify(self.name, allow_unicode=True)
            slug = base_slug
            counter = 1
            # چک می‌کنیم اسلاگ تکراری نباشه، اگه بود یه عدد تهش می‌ندازیم
            while self.__class__.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.name

class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories', verbose_name=_("دسته اصلی"))
    name = models.CharField(max_length=100, verbose_name=_("نام زیردسته"))
    slug = models.SlugField(unique=True, blank=True, verbose_name=_("اسلاگ"))
    description = models.TextField(blank=True, null=True, verbose_name=_("توضیحات"))

    class Meta:
        verbose_name = _("زیردسته")
        verbose_name_plural = _("زیردسته‌ها")
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


#  مدل خدمات سالن
class Service(models.Model):
    image = models.ImageField(upload_to='services/', blank=True, null=True, verbose_name="عکس اصلی")
    name = models.CharField(max_length=200, verbose_name=_("نام خدمت"))
    # توضیحات  
    description = models.TextField(blank=True, null=True,verbose_name=_("توضیحات"))
    # مدت زمان انجام  
    duration_minutes = models.IntegerField(default=30,verbose_name=_("مدت زمان (دقیقه)"))
    price = models.PositiveBigIntegerField(verbose_name=_("قیمت (تومان)"))
    # وضعیت فعال/غیرفعال بودن 
    is_active = models.BooleanField(default=True,verbose_name=_("فعال است"))
    #ارتباط با زیردسته
    subcategory = models.ForeignKey(Subcategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='services', verbose_name=_("زیردسته"))
    slug = models.SlugField(unique=True, blank=True, verbose_name=_("اسلاگ"))
    # ارتباط با دسته اصلی
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='services', verbose_name=_("دسته اصلی"))
    
    @property
    def duration_display(self):
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60

        if hours and minutes:
            return f"{hours} ساعت و {minutes} دقیقه"
        elif hours:
            return f"{hours} ساعت"
        else:
            return f"{minutes} دقیقه"


    @property
    def image_url(self):
        if self.image:
            return self.image.url
        return static('images/service.png')

    class Meta:
        verbose_name = _("خدمت")
        verbose_name_plural = _("خدمات")

    def price_in_words(self):
        return number_to_persian_words(self.price)

    def approved_reviews(self):
        #کامنت‌های تایید شده رو فیلتر میکنه
        return self.reviews.filter(service=self, status='approved').order_by('-created_at')
    
    def get_related_images(self):
        # گرفتن عکس‌های گالری سرویس
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
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.service.name} - Image {self.id}"

#برای خدمات پرطرفدار
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
        # همیشه بر اساس ترتیبی که ادمین داده (order) مرتبشون کن
        ordering = ['order']
        verbose_name = "خدمت پرطرفدار"
        verbose_name_plural = "خدمات پرطرفدار"

    def __str__(self):
        if self.category:
            return f"{self.title} ({self.category.name})"
        return f"{self.title} (بدون دسته‌بندی)"

