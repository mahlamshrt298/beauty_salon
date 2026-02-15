from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages
from .forms import CustomRegisterForm
from django.contrib.auth import logout
from django.contrib.auth.models import User
from .models import Profile
from booking.models import Appointment ,Payment
from .models import Notification
import re
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from reviews_app.models import Review
import jdatetime
from datetime import date
import os
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordChangeView
from .forms import ReviewForm
from services_app.models import Service
from django.template.loader import render_to_string
from django.utils import timezone
from booking.models import Appointment
from booking.views import MAX_ACTIVE_APPOINTMENTS_PER_USER  # اگر این ثابت در booking تعریف شده
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from core.models import PackageBooking

class MyPasswordChangeView(PasswordChangeView):
    template_name = "password_change.html"       # قالب شما
    success_url = reverse_lazy("accounts:profile")      # پس از موفقیت به پروفایل برگرد

# Create your views here.
def register(request):
    # اگر درخواست POSTباشد: اطلاعات فرم را پردازش و کاربر جدید ایجاد می‌کند
    # اگر درخواست GET باشد: فرم خالی ثبت‌نام را نمایش می‌دهد
    if request.method=="POST":
        #گرفتن داده‌های ارسالی
        register_form = CustomRegisterForm(request.POST)
        #بررسی صحت داده‌ها
        if register_form.is_valid():
            register_form.save()    # ذخیره   در دیتابیس
            
            #نمایش پیام
            messages.success(request,  "ثبت‌نام شما با موفقیت انجام شد! اکنون می‌توانید وارد شوید.", extra_tags = "front")
           
           ## هدایت  به صفحه ثبت‌نام مجدد (تغییرش بده به لاگین یا خونه)
            return redirect('home')
    else:
        
        # ایجاد فرم خالی برای نمایش به کاربر
        register_form = CustomRegisterForm()
    return render(request,'register.html',{'register_form':register_form})

def custom_logout(request):
    #ویو سفارشی برای خروج   در اخر یه صفحه تایید نشون میده
    logout(request)  # کاربر را خارج می‌کند
    return render(request, 'logout.html')  # بعد از خروج صفحه logout.html را نشان بده

@login_required
def profile(request):
    user = request.user

    # پروفایل اگر نبود، ساخته شود
    profile, created = Profile.objects.get_or_create(user=user)

    if request.method == 'POST':

        # -------------------------------
        #  ذخیره تنظیمات یادآوری
        # -------------------------------
        if 'save_reminder' in request.POST:
            reminder_enabled = request.POST.get('reminder_enabled') == 'on'
            profile.reminder_enabled = reminder_enabled
            profile.save()
            messages.success(request, "تنظیمات یادآوری ذخیره شد.", extra_tags = "front")
            return redirect('accounts:profile')

        profile = request.user.profile

            # 🔴 حذف آواتار
        if 'delete_avatar' in request.POST:
            if profile.avatar:
                avatar_path = profile.avatar.path

                # حذف فایل از سیستم
                if os.path.isfile(avatar_path):
                    os.remove(avatar_path)

                # پاک‌کردن مقدار از دیتابیس
                profile.avatar = None
                profile.save()

                # ✅ پیام موفقیت
                messages.success(request, "عکس پروفایل با موفقیت حذف شد.")

            return redirect('accounts:profile')
        # -------------------------------
        #  ذخیره اطلاعات پروفایل
        # -------------------------------
        if 'save_profile' in request.POST:

            # نام کامل
            full_name = request.POST.get('full_name', '').strip()
            if full_name:
                # اگر کاربر فیلد first_name و last_name جدا نمی‌خواست دارد،
                # می‌تونی full_name رو کامل ذخیره کنی:
                name_parts = full_name.split(' ', 1)
                user.first_name = name_parts[0]
                if len(name_parts) > 1:
                    user.last_name = name_parts[1]

            # ایمیل
            email = request.POST.get('email')
            if email and email != user.email:
                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    messages.error(request, "این ایمیل قبلاً ثبت شده است.", extra_tags = "front")
                    return redirect('accounts:profile')
                user.email = email

            user.save()

            # فیلدهای پروفایل
            phone = request.POST.get('phone', '').strip()

            if phone:
                # اعتبارسنجی شماره موبایل ایران
                if not re.fullmatch(r'09\d{9}', phone):
                    messages.error(
                        request,
                        "شماره موبایل باید با 09 شروع شود و دقیقاً 11 رقم باشد.",
                        extra_tags="front"
                    )
                    return redirect('accounts:profile')

            profile.phone = phone
            
            bio = request.POST.get('bio', '')
            if len(bio) > 300:
                messages.error(
                    request,
                    "بیوگرافی نباید بیشتر از ۳۰۰ کاراکتر باشد.",
                    extra_tags="front"
                )
                return redirect('accounts:profile')
            profile.bio = bio
            
            # آواتار
            MAX_WIDTH, MAX_HEIGHT = 800, 800    # حداکثر ابعاد پیکسل

            avatar = request.FILES.get('avatar')
            if avatar :
                if  avatar.size > 1 * 1024 * 1024:
                    messages.error(request, "حجم عکس نباید بیشتر از 1 مگابایت باشد.")
                    return redirect("accounts:profile")

            # ابعاد و فشرده‌سازی
                try:
                    img = Image.open(avatar)
                    img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)

                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=85)  # فشرده‌سازی
                    buffer.seek(0)

                    avatar = InMemoryUploadedFile(
                        buffer, None, avatar.name, 'image/jpeg',
                        buffer.tell(), None
                    )
                except Exception:
                    messages.error(request, "فرمت تصویر نامعتبر است.")
                    return redirect("accounts:profile")

                profile.avatar = avatar
            # -------------------------------
            #  تاریخ تولد (شمسی → میلادی)
            # -------------------------------
            # -------------------------------
            #  تاریخ تولد (سال / ماه / روز شمسی)
            # -------------------------------
            birth_year = request.POST.get("birth_year")
            birth_month = request.POST.get("birth_month")
            birth_day = request.POST.get("birth_day")

            if birth_year and birth_month and birth_day:
                # اگر قبلاً تاریخ تولد ثبت شده و بیش از ۲ بار تغییر داده
                if profile.birthday and profile.birthday_change_count >= 2:
                    messages.error(
                        request,
                        "شما فقط تا ۲ بار امکان تغییر تاریخ تولد را دارید.",
                        extra_tags="front"
                    )
                    return redirect("accounts:profile")
                try:
                    jalali_date = jdatetime.date(
                        int(birth_year),
                        int(birth_month),
                        int(birth_day)
                    )
                    new_gregorian_date = jalali_date.togregorian()

                      # ❌ تاریخ آینده نباشد
                    if new_gregorian_date > date.today():
                        messages.error(
                            request,
                            "تاریخ تولد نمی‌تواند در آینده باشد.",
                            extra_tags="front"
                        )
                        return redirect("accounts:profile")

                     # فقط اگر تاریخ جدید با قبلی فرق دارد، شمارنده افزایش یابد
                    if profile.birthday != new_gregorian_date:
                        if profile.birthday:
                            profile.birthday_change_count += 1
                        profile.birthday = new_gregorian_date
                        
                except ValueError:
                    profile.save()
                    messages.error(
                        request,
                        "تاریخ تولد نامعتبر است.",
                        extra_tags="front"
                    )
                    return redirect('accounts:profile')
            # ذخیره نهایی تغییرات پروفایل
            profile.save()
            messages.success(request, "اطلاعات با موفقیت ذخیره شد.", extra_tags="front")
            return redirect('accounts:profile')


    # -------------------------------
    #  ارسال اطلاعات به قالب
    # -------------------------------
    # -------------------------------
    #  ارسال اطلاعات به قالب
    # -------------------------------
    # ✅ دریافت فیلتر وضعیت از URL
    status_filter = request.GET.get('status', 'all')  # اضافه شد

    appointments = None
    try:
        # ✅ اعمال فیلتر وضعیت
        if status_filter == 'all':
            appointments_queryset = Appointment.objects.filter(user=user)
        else:
            appointments_queryset = Appointment.objects.filter(user=user, status=status_filter)
        
        appointments_queryset = appointments_queryset.select_related(
            'service',
            'staff',
            'service__subcategory',
            'service__subcategory__category',
            'package_booking__package'
        ).order_by('-appointment_date')
        
        # ✅ اضافه کردن اطلاعات پرداخت به هر نوبت (بدون تغییر)
        appointments_list = []

        for appt in appointments_queryset:
            try:
                payment = appt.payment
            except Payment.DoesNotExist:
                payment = None
                        
            # 🔵 بررسی اینکه نوبت مربوط به پکیج است یا خیر
            package_booking = getattr(appt, "package_booking", None)

            if package_booking and package_booking.package:
                appt.is_from_package = True
                appt.package_title = package_booking.package.title
            else:
                appt.is_from_package = False
                appt.package_title = None


            if payment:
                appt.payment_info = {
                    'amount': payment.amount,
                    'method': payment.payment_method,
                    'method_display': payment.get_payment_method_display(),
                    'original_price': appt.service.price,
                    'discount_amount': appt.service.price - payment.amount if payment.amount < appt.service.price else 0,
                    'discount_percent': round(((appt.service.price - payment.amount) / appt.service.price) * 100, 0) if payment.amount < appt.service.price else 0,
                }

                
            else:
                appt.payment_info = None
            appointments_list.append(appt)
        

        paginator = Paginator(appointments_list, 5)  # 👈 ۵ نوبت در هر صفحه
        page_number = request.GET.get("appointments_page")
        appointments = paginator.get_page(page_number)

    except Exception as e:
        print(f"Error loading appointments: {e}")
        appointments = None
        
    user_reviews = Review.objects.filter(user=user).select_related("appointment", "service").order_by('-created_at')

    reviews_paginator = Paginator(user_reviews, 4)
    reviews_page = request.GET.get("reviews_page")
    user_reviews = reviews_paginator.get_page(reviews_page)

    current_jalali_year = jdatetime.date.today().year

    
    today = timezone.localdate()

    active_appointments_count = Appointment.objects.filter(
        user=user,
        status__in=['pending', 'confirmed'],
        appointment_date__gte=today
    ).count()

    remaining_quota = MAX_ACTIVE_APPOINTMENTS_PER_USER - active_appointments_count

    has_any_appointment = Appointment.objects.filter(user=user).exists()

    return render(request, 'profile.html', {
        'user': user,
        'profile': profile,
        'appointments': appointments,
        'birth_years': range(1350, current_jalali_year + 1),
        'user_reviews': user_reviews, 
        'status': status_filter,
            # ✅ این خط جدید اضافه شد
        'active_appointments_count': active_appointments_count,
        'remaining_quota': remaining_quota,
        'max_quota': MAX_ACTIVE_APPOINTMENTS_PER_USER,
        'has_any_appointment': has_any_appointment,


    })


def login_view(request):
    next_url = request.GET.get("next", "/")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            if user.profile.role in ['owner', 'receptionist']:
                # برای پرسنل به داشبورد
                return redirect('panel:dashboard')
            # برای کاربران عادی به پروفایل
            return redirect('accounts:profile')
        else:
            messages.error(request, "نام کاربری یا رمز عبور اشتباه است.", extra_tags= "front")

    return render(request, "login.html", {"next": next_url})

@login_required
def notifications_list(request):
    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-created_at")

    paginator = Paginator(notifications, 10)  # 👈 ۱۰ اعلان در هر صفحه
    page_number = request.GET.get("page")
    notifications = paginator.get_page(page_number)

    return render(
        request,
        "notifications_list.html",
        {"notifications": notifications}
    )


@login_required
def ajax_add_review(request, appointment_id):
    appointment = get_object_or_404(
        Appointment,
        id=appointment_id,
        user=request.user,
        status='completed'
    )

    service = appointment.service

     # ✅ آیا این کاربر برای این خدمت نوبت انجام‌شده دارد؟
    has_done_appointment = Appointment.objects.filter(
        user=request.user,
        service=service,
        status='completed'
    ).exists()

    if not has_done_appointment:
        return JsonResponse({
            'success': False,
            'error': 'شما فقط می‌توانید برای خدمات انجام‌شده نظر ثبت کنید.'
        }, status=403)
    
    # تعداد کل نظرات این نوبت
    total_reviews = Review.objects.filter(
        user=request.user,
        appointment=appointment
    ).count()

    # تعداد نظرات تایید نشده این نوبت
    pending_reviews = Review.objects.filter(
        user=request.user,
        appointment=appointment,
        status='pending'
    ).count()

    # اگر نظر در انتظار تایید دارد → اجازه ثبت نده
    if pending_reviews > 0:
        return JsonResponse({
            'success': False,
            'error': 'نظر قبلی شما هنوز تأیید نشده است.'
        }, status=403)

    # اگر ۲ نظر ثبت شده → اجازه ثبت نده
    if total_reviews >= 2:
        return JsonResponse({
            'success': False,
            'error': 'شما برای این نوبت بیش از ۲ نظر نمی‌توانید ثبت کنید.'
        }, status=403)

    if request.method == "POST":
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        # ✅ اعتبارسنجی امتیاز
        if not rating or not rating.isdigit() or not (1 <= int(rating) <= 5):
            return JsonResponse({
                'success': False,
                'errors': {'rating': ['امتیاز نامعتبر است']}
            }, status=400)

        form = ReviewForm(request.POST)
        if form.is_valid():
            rev = form.save(commit=False)
            rev.user = request.user
            rev.service = service
            rev.appointment = appointment
            rev.save()
            return JsonResponse({'success': True})

        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)
    else:
        form = ReviewForm()
        html = render_to_string(
            'review_form.html',
            {'form': form, 'appointment': appointment},
            request=request
        )
        return JsonResponse({'html': html})

@login_required
def cancel_appointment(request, appt_id):
    appt = get_object_or_404(Appointment, id=appt_id, user=request.user)

    if not appt.can_cancel_by_user():
        messages.error(request, "لغو نوبت فقط تا ۲۴ ساعت قبل امکان‌پذیر است.")
        return redirect('accounts:profile')

    appt.status = 'cancelled'
    appt._skip_signal = True    # 👈 جلوگیری از ارسال سیگنال
    appt.save()

    # اعلان داخلی
    Notification.objects.create(
        user=request.user,
         appointment=appt,
        type='status_change',
        status='sent',
        channel='email',  # یا sms / whatsapp
        message=f"نوبت شما برای خدمت {appt.service.category.name} : {appt.service.subcategory.name} : {appt.service.name}  در تاریخ {appt.jalali_date_display} و ساعت : {appt.start_time}با موفقیت لغو شد."
       )

    # ایمیل
    send_mail(
        subject="لغو نوبت",
        message=f"نوبت شما برای {appt.service.name} لغو شد.",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[request.user.email],
        fail_silently=True
    )

    messages.success(request, "نوبت با موفقیت لغو شد.")
    return redirect('accounts:profile')
