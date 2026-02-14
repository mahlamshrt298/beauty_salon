from django.shortcuts import render, redirect,get_object_or_404
from .models import Review
from django.core.paginator import Paginator
from django.db.models import Avg
from .forms import ReviewForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from services_app.models import Service , Category
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q  # در ابتدای فایل اضافه کنید

DAILY_REVIEW_LIMIT = 2     # حداکثر ۲ نظر در روز

#لیست  نظرات تأیید شده
def reviews_list(request):
    # ✅ جایگزینی فیلتر سرویس با فیلتر دسته‌بندی
    all_categories = Category.objects.annotate(
        review_count=Count(
            'subcategories__services__reviews', 
            filter=Q(subcategories__services__reviews__status='approved')
        )
    ).order_by('name')   

    # دریافت پارامتر فیلتر دسته‌بندی
    category_id = request.GET.get('category')  # ← تغییر از 'service' به 'category'
    
    # فیلتر نظرات بر اساس سرویس
    reviews_queryset = Review.objects.filter(status='approved')
    if category_id and category_id != 'all':
        reviews_queryset = reviews_queryset.filter(service__subcategory__category_id=category_id)
    
    # سایر محاسبات(میانگین و تعداد کل نظرات)
    avg_rating = reviews_queryset.aggregate(avg=Avg('rating'))['avg']
    total_reviews = reviews_queryset.count()
    
    #مرتب‌سازی و صفحه‌بندی(8نظر در هر صفحه)
    reviews = reviews_queryset.select_related('user', 'service').order_by('-created_at')
    paginator = Paginator(reviews, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        # هدایت کاربران لاگین نکرده به صفحه ورود
        if not request.user.is_authenticated:
            # هدایت به صفحه لاگین با next
            return redirect(f"{reverse('login')}?next={request.path}")
            
        form = ReviewForm(request.POST, user=request.user)
        if form.is_valid():
           # service = form.cleaned_data.get('service')

 # ---------- شروع محدودیت روزانه ----------
            today = timezone.now().date()
            today_reviews = Review.objects.filter(
                user=request.user,
                created_at__date=today
            ).count()

            if today_reviews >= DAILY_REVIEW_LIMIT:
                messages.error(
                    request,
                    f"حداکثر {DAILY_REVIEW_LIMIT} نظر در هر روز می‌توانید ثبت کنید.",
                    extra_tags="front",
                )
                return redirect('reviews')   # یا هر آدرس مناسبی
            # ---------- پایان محدودیت ----------

            appointment = form.cleaned_data['appointment']

            # ✅ محدودیت: حداکثر 2 نظر برای هر نوبت
            reviews_for_appointment = Review.objects.filter(
                user=request.user,
                appointment=appointment
            ).count()
            if reviews_for_appointment >= 2:
                messages.error(
                    request,
                    "شما برای این نوبت به حداکثر تعداد نظرات (2 نظر) رسیده‌اید.",
                    extra_tags="front"
                )
                return redirect('reviews')

            review = form.save(commit=False)
            review.user = request.user
            review.service = appointment.service  # ✅ تنظیم خدمت از روی نوبت
            review.status = 'pending' 
            review.save()
            messages.success(request, 'نظر شما با موفقیت ارسال شد و پس از بررسی نمایش داده خواهد شد.', extra_tags = "front")
            return redirect('reviews')
    else:
        # ✅ برای درخواست GET: ایجاد فرم با فیلتر نوبت‌ها
        form = ReviewForm(user=request.user)

    selected_category = None
    if category_id and category_id != 'all':
        try:
            selected_category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            pass

    context = {
        'avg_rating': avg_rating,   # میانگین امتیاز
        'total_reviews': total_reviews,     # تعداد کل نظرات
        'page_obj': page_obj,
        'form': form,
        'all_categories': all_categories,
          'selected_category': selected_category,  # ← ارسال لیست سرویس‌ها
        'active_page': 'reviews',  # برای هایلایت منوی فعال
    }
    return render(request, 'reviews/reviews.html', context)


@login_required     # فقط کاربران وارد شده می‌توانند نظر بدن
def add_review_for_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
        # ---------- محدودیت ۲ نظر در روز ----------
    today = timezone.now().date()
    reviews_today = Review.objects.filter(
        user=request.user,
        created_at__date=today
    ).count()
    if reviews_today >= DAILY_REVIEW_LIMIT:
        messages.error(
            request,
            f"در هر روز می‌توانید حداکثر {DAILY_REVIEW_LIMIT} نظر ثبت کنید.",
            extra_tags="front",
        )
        return redirect('service_detail', pk=service.id)
    # -------------------------------------------

  # ✅ محدودیت ۵ نظر برای هر خدمت
    reviews_count = Review.objects.filter(
        user=request.user,
        service=service
    ).count()

    if reviews_count >= 5:
        messages.error(
            request,
            "شما حداکثر می‌توانید ۵ نظر برای این خدمت ثبت کنید.",
            extra_tags="front"
        )
        return redirect('service_detail', pk=service.id)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.service = service  # ← سرویس به‌صورت خودکار تنظیم می‌شود
            review.save()
            messages.success(request, 'نظر شما با موفقیت ارسال شد و پس از بررسی نمایش داده خواهد شد.', extra_tags = "front")
            return redirect('service_detail', pk=service.id)
    else:
        form = ReviewForm()
    
    # این تابع فقط برای پست است، پس معمولاً مستقیم تمپلیت نمی‌دهد
    return redirect('service_detail', pk=service.id)

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)

    review.delete()
    messages.success(request, "نظر شما با موفقیت حذف شد.", extra_tags="front")
    return redirect('accounts:profile')

@login_required
def edit_review(request, review_id):
    review = get_object_or_404(
        Review,
        id=review_id,
        user=request.user,
        status='pending'
    )

    if request.method == 'POST':
        review.comment = request.POST.get('comment')
        review.rating = int(request.POST.get('rating'))
        review.save()

        messages.success(
            request,
            "نظر شما ویرایش شد و دوباره در انتظار تأیید قرار گرفت.",
            extra_tags="front"
        )
        return redirect('accounts:profile')

    return render(request, 'reviews/edit_review.html', {
        'review': review
    })
