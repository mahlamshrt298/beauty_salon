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
from django.db.models import Count, Q  

DAILY_REVIEW_LIMIT = 2     # حداکثر ۲ نظر در روز

#لیست  نظرات تأیید شده
def reviews_list(request):
    # فیلتر دسته‌بندی
    all_categories = Category.objects.annotate(
        review_count=Count(
            'subcategories__services__reviews', 
            filter=Q(subcategories__services__reviews__status='approved')
        )
    ).order_by('name')   

    # دریافت پارامتر فیلتر دسته‌بندی
    category_id = request.GET.get('category') 
    
    reviews_queryset = Review.objects.filter(status='approved')
    if category_id and category_id != 'all':
        reviews_queryset = reviews_queryset.filter(service__subcategory__category_id=category_id)
    
    #میانگین و تعداد کل نظرات
    avg_rating = reviews_queryset.aggregate(avg=Avg('rating'))['avg']
    total_reviews = reviews_queryset.count()
    
    reviews = reviews_queryset.select_related('user', 'service').order_by('-created_at')
    paginator = Paginator(reviews, 8)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
            
        form = ReviewForm(request.POST, user=request.user)
        if form.is_valid():

            # چک کردن محدودیت ثبت نظر روزانه
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
                return redirect('reviews')

            appointment = form.cleaned_data['appointment']

            #  محداکثر 2 نظر برای هر نوبت
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
            review.service = appointment.service  #  تنظیم خدمت از روی نوبت
            review.status = 'pending' 
            review.save()
            messages.success(request, 'نظر شما با موفقیت ارسال شد و پس از بررسی نمایش داده خواهد شد.', extra_tags = "front")
            return redirect('reviews')
    else:
        form = ReviewForm(user=request.user)

    # برای اکتیو کردن دسته انتخاب شده توی فرانت
    selected_category = None
    if category_id and category_id != 'all':
        try:
            selected_category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            pass

    context = {
        'avg_rating': avg_rating,   
        'total_reviews': total_reviews,  
        'page_obj': page_obj,
        'form': form,
        'all_categories': all_categories,
          'selected_category': selected_category, 
        'active_page': 'reviews',  
    }
    return render(request, 'reviews/reviews.html', context)


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
