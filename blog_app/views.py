# Create your views here.
from django.shortcuts import render, get_object_or_404
from .models import Article, Category
from django.core.paginator import Paginator
from django.db.models import Q,Count , F
from django.http import JsonResponse

def blog_list(request):
        # دریافت پارامترهای فیلتر و جستجو از URL
    category_slug = request.GET.get('category', None)
     # حذف فاصله‌های اضافه از عبارت جستجو
    query = request.GET.get('q', '').strip()  # ← strip() برای حذف فاصله‌های اضافه

    articles = Article.objects.select_related('category', 'author').all()

    # جست‌وجوی هوشمند (فقط اگر عبارت جست‌وجو خالی نباشد)
    if query:
        articles = articles.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query)
        )

    # فیلتر دسته‌بندی
    if category_slug:
        articles = articles.filter(category__name__icontains=category_slug)

# مرتب‌سازی مقالات از جدیدترین به قدیمی‌ترین
    articles = articles.order_by('-created_at')
    categories = Category.objects.annotate(
        articles_count=Count('article')
    )
    
    # صفحه‌بندی  - 6 مقاله در هر صفحه
    paginator = Paginator(articles, 6)
    page_number = request.GET.get('page',1)
    page_obj = paginator.get_page(page_number)

    # ارسال اطلاعات برای نمایش پیام "نتیجه‌ای یافت نشد"
    no_results = (query and not articles.exists())

    return render(request, 'blog/blog.html', {
        'page_obj': page_obj,    # مقالات صفحه‌بندی شده
        'categories': categories,   # لیست تمام دسته‌بندی‌ها
        'selected_category': category_slug,      # دسته‌بندی انتخاب شده
        'search_query': query,      # عبارت جستجو شده
        'no_results': no_results,  #  برای نمایش پیام خطا
        'active_page': 'blog',  # برای هایلایت منوی فعال
    })


def blog_detail(request, pk):
    article = get_object_or_404(Article, pk=pk)

    # ✅ افزایش تعداد بازدید (امن و حرفه‌ای)
    article.views_count = F('views_count') + 1
    article.save(update_fields=['views_count'])
    article.refresh_from_db()

    # استخراج برچسب‌ها به صورت لیست
    if article.tags:
        tag_list = [tag.strip() for tag in article.tags.split('،') if tag.strip()]
    else:
        tag_list = []

    # مقالات مرتبط بر اساس برچسب‌های مشترک
    related_articles = Article.objects.none()  # شروع با QuerySet خالی

    if tag_list:
        # ساخت کوئری برای جستجوی مقالات با برچسب‌های مشترک
        query = Q()
        for tag in tag_list:
            query |= Q(tags__icontains=tag)
        
        related_articles = Article.objects.filter(query).exclude(pk=article.pk).order_by('-created_at')[:3]

    # اگر مقاله‌ای بر اساس برچسب پیدا نشد، بر اساس دسته‌بندی بگرد
    if not related_articles.exists():
        related_articles = Article.objects.filter(
            category=article.category
        ).exclude(pk=article.pk).order_by('-created_at')[:3]

    return render(request, 'blog/blog_detail.html', {'article': article ,  'related_articles': related_articles , 'active_page': 'blog', })

#برای جستجوی زنده در وبلاگ
def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    suggestions = []
    if len(query) >= 2:  # حداقل 2 کاراکتر برای جست‌وجو
        articles = Article.objects.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).values('title', 'id')[:5]  # 5 نتیجه اول
        # ساخت لیست پیشنهادات با عنوان و لینک
        suggestions = [{'title': a['title'], 'url': f"/blog/{a['id']}/"} for a in articles]
    return JsonResponse(suggestions, safe=False)