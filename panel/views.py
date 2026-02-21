from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from booking.models import Appointment,Staff
from services_app.models import ( Service ,PopularService, ServiceImage, Category as ServiceCategory, Subcategory,)
from django.db.models import Q , Count
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_POST
from .models import ContactMessage
from core.models import SalonSettings
from accounts.models import Profile, Notification, DiscountCode
from datetime import datetime, timedelta , date
import jdatetime
from blog_app.models import (Article, Category as BlogCategory,)
import re
from services_app.models import PopularService
import json
from .forms import DiscountCodeForm
from django.contrib.auth import get_user_model
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django.db import transaction
import logging
logger = logging.getLogger(__name__)  
from django.core.mail import send_mass_mail
from booking.models import Payment , Holiday
from django.db.models import Q
from services_app.forms import ServiceForm, ServiceGalleryForm
from accounts.models import DiscountCode
from core.models import Package
from django.contrib import messages
from accounts.models import Notification
from django.core.paginator import Paginator
from django.forms import modelformset_factory
from reviews_app.models import Review
from .forms import DiscountCodeForm
from functools import wraps

def panel_access_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')

        if not request.user.groups.filter(name__in=["owner", "receptionist"]).exists():
            return redirect('panel:no_access')

        return view_func(request, *args, **kwargs)

    return _wrapped_view


# داشبورد
# -----------------------------
@login_required
@panel_access_required
def dashboard(request):
    JALALI_MONTHS = {
        "01": "فروردین",
        "02": "اردیبهشت",
        "03": "خرداد",
        "04": "تیر",
        "05": "مرداد",
        "06": "شهریور",
        "07": "مهر",
        "08": "آبان",
        "09": "آذر",
        "10": "دی",
        "11": "بهمن",
        "12": "اسفند",
    }

    # دریافت ماه و سال از querystring
    year = request.GET.get("year")
    month = request.GET.get("month")

    appointments = Appointment.objects.all()

    if year and month:
        jy = int(year)
        jm = int(month)

        start_j = jdatetime.date(jy, jm, 1)

        # ✅ محاسبه امن انتهای ماه شمسی
        end_j = start_j.replace(day=1) + jdatetime.timedelta(days=32)
        end_j = end_j.replace(day=1)

        start_g = start_j.togregorian()
        end_g = end_j.togregorian()

        appointments = appointments.filter(
            appointment_date__gte=start_g,
            appointment_date__lt=end_g
        )

    total_appointments = appointments.count()
    total_services = Service.objects.count()
    total_staff = User.objects.filter(groups__name="receptionist").count()

    # شمارش وضعیت‌ها
    pending_bookings = appointments.filter(status="pending").count()
    confirmed = appointments.filter(status="confirmed").count()
    pending = appointments.filter(status="pending").count()
    cancelled = appointments.filter(status="cancelled").count()
    completed = appointments.filter(status="completed").count()

    # ✅ این دو خط جدید
    years = [str(y) for y in range(1404, 1412)]
    months = [str(i).zfill(2) for i in range(1, 13)]


    return render(request, "panel/dashboard.html", {
        "total_appointments": total_appointments,
        "total_services": total_services,
        "total_staff": total_staff,

        "pending_bookings": pending_bookings,

        # برای نمودار
        "confirmed": confirmed,
        "pending": pending,
        "cancelled": cancelled,
        "completed": completed,

        # برای حفظ انتخاب فیلتر
        "years": years,
        "months": months,
        "selected_year": year,
        "selected_month": month,
        })

# مدیریت نوبت‌ها
# -----------------------------

@login_required
@panel_access_required
def booking_list(request):
    appointments = Appointment.objects.select_related("user", "service").order_by("-id")
   # 🔍 سرچ متنی
    q = request.GET.get("q")
    if q:
        appointments = appointments.filter(
            Q(user__username__icontains=q) |
            Q(service__name__icontains=q) |
            Q(status__icontains=q)
        )

    # 🔽 فیلتر وضعیت
    status = request.GET.get("status")
    if status:
        appointments = appointments.filter(status=status)

    # ✅ فیلتر بازه زمانی تاریخ شمسی
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    if start_date and end_date:
        try:
            # تبدیل تاریخ شمسی به میلادی برای فیلتر
            start_parts = start_date.split('/')
            end_parts = end_date.split('/')
            
            if len(start_parts) == 3 and len(end_parts) == 3:
                start_year = int(start_parts[0])
                start_month = int(start_parts[1])
                start_day = int(start_parts[2])
                end_year = int(end_parts[0])
                end_month = int(end_parts[1])
                end_day = int(end_parts[2])
                
                start_jalali_date = jdatetime.date(start_year, start_month, start_day)
                end_jalali_date = jdatetime.date(end_year, end_month, end_day)
                
                start_gregorian_date = start_jalali_date.togregorian()
                end_gregorian_date = end_jalali_date.togregorian()
                
                appointments = appointments.filter(
                    appointment_date__gte=start_gregorian_date,
                    appointment_date__lte=end_gregorian_date
                )
        except (ValueError, IndexError, jdatetime.datetime.DateError):
            # در صورت خطا، فیلتر تاریخ نادیده گرفته می‌شود
            pass 

    # در ویو booking_list، در بخش پردازش appointments
    converted_appointments = []
    month_names = {  # ← تغییر از "month1:" به "month_names ="
        1: "فروردین",
        2: "اردیبهشت",
        3: "خرداد",
        4: "تیر",
        5: "مرداد",
        6: "شهریور",
        7: "مهر",
        8: "آبان",
        9: "آذر",
        10: "دی",
        11: "بهمن",
        12: "اسفند",
    }

    for item in appointments:
        # ✅ تبدیل کامل تاریخ میلادی به شمسی
        j_date = jdatetime.date.fromgregorian(date=item.appointment_date)
        
        # ✅ ایجاد تاریخ شمسی کامل (روز، ماه، سال)
        item.shamsi_date = f"{j_date.day} {month_names[j_date.month]} {j_date.year}"
        
        # --- بقیه کد‌ها (ساعت و ...)
        t = item.start_time
        hour = t.hour
        minute = t.minute
        suffix = "a.m" if hour < 12 else "p.m"
        hour12 = hour % 12
        if hour12 == 0:
            hour12 = 12
        item.fixed_time = f"{hour12}:{minute:02d} {suffix}"
        
        item.is_past = item.is_past_and_not_completed()
        item.notes_preview = item.notes[:30] + '...' if item.notes and len(item.notes) > 30 else item.notes
        
        # ✅ محاسبه شماره‌های تماس برای هر نوبت
        profile_phone = None
        if hasattr(item.user, 'profile') and item.user.profile.phone:
            profile_phone = item.user.profile.phone
        
        appt_phone = item.phone
        
        # ✅ اگر هر دو وجود دارند و متفاوت هستند
        if profile_phone and appt_phone and profile_phone != appt_phone:
            item.display_phones = [
                {'number': profile_phone, 'label': 'پروفایل'},
                {'number': appt_phone, 'label': 'رزرو'}
            ]
         # ✅ اگر فقط یکی وجود دارد
        elif profile_phone:
            item.display_phones = [{'number': profile_phone, 'label': 'پروفایل'}]
        elif appt_phone:
            item.display_phones = [{'number': appt_phone, 'label': 'رزرو'}]
        else:
            item.display_phones = None
            
        converted_appointments.append(item)
        
    paginator = Paginator(converted_appointments, 10)  # 10 نوبت در هر صفحه
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "panel/booking_list.html",
        {"appointments": page_obj,  "q": q, "status": status,"start_date": start_date, 
        "end_date": end_date  },
    )

@require_POST
@login_required
@panel_access_required
def booking_approve(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    appointment.status = "confirmed"
    appointment.save()

    messages.success(request, "نوبت تأیید شد.", extra_tags = "panel")
    return redirect("panel:booking_list")

@require_POST
@login_required
@panel_access_required
def booking_cancel(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    appointment.status = "cancelled"
    appointment.save()

    messages.error(request, "نوبت لغو شد.", extra_tags = "panel")
    return redirect("panel:booking_list")

@login_required
@panel_access_required
def booking_update(request, booking_id):
    appointment = get_object_or_404(Appointment, id=booking_id)
    # 🔒 فقط نوبت‌های pending و confirmed قابل ویرایش هستند
    if appointment.status not in ["pending", "confirmed"]:
        messages.warning(request, "این نوبت قابل ویرایش نیست.", extra_tags="panel")
        return redirect("panel:booking_list")
  
    # 🔒 قفل ویرایش نوبت تأییدشده برای غیر مدیر
    if appointment.status == "confirmed" and request.user.profile.role not in ["owner", "receptionist"]:
        messages.warning(
            request,
            "نوبت تأیید شده است و فقط مدیر می‌تواند آن را ویرایش کند." , extra_tags = "panel"
        )
        return redirect("panel:booking_list")

    if request.user.profile.role not in ["owner", "receptionist"]:
        messages.error(request, "شما اجازه ویرایش ندارید" , extra_tags = "front")
        return redirect("panel:booking_list")
    else:
        if request.method == "POST":
            new_date_str = request.POST.get("date")  # مثال: "1404/12/16"
            new_time_str = request.POST.get("start_time")
            service_id = request.POST.get("service")
            staff_id = request.POST.get("staff")

            if not new_time_str:
                messages.error(request, "ساعت نوبت ارسال نشده است", extra_tags="panel")
                return redirect("panel:booking_update", booking_id=booking_id)

            # ✅ تبدیل تاریخ شمسی به میلادی
            try:
                jy, jm, jd = map(int, new_date_str.split("/"))
                new_date_gregorian = jdatetime.date(jy, jm, jd).togregorian()

                # ✅ اعتبارسنجی: تاریخ نباید دیروز یا قبل‌تر باشد
                today_jalali = jdatetime.date.today()
                yesterday_jalali = today_jalali - jdatetime.timedelta(days=1)
                selected_jalali = jdatetime.date(jy, jm, jd)
                
                if selected_jalali <= yesterday_jalali:
                    messages.error(
                        request, 
                        "تاریخ نمی‌تواند دیروز یا قبل‌تر باشد. لطفاً تاریخ امروز یا آینده را انتخاب کنید.",
                        extra_tags="panel"
                    )
                    return redirect("panel:booking_update", booking_id=booking_id)

            except (ValueError, AttributeError):
                messages.error(request, "فرمت تاریخ نامعتبر است. لطفاً از فرمت 1404/12/16 استفاده کنید.", extra_tags="panel")
                return redirect("panel:booking_update", booking_id=booking_id)

            # 🔹 گرفتن سرویس
            service = get_object_or_404(Service, id=service_id)

            # 🔹 تبدیل ساعت
            start_time = datetime.strptime(new_time_str, "%H:%M").time()

            # 🔹 محاسبه end_time
            dt = datetime.combine(new_date_gregorian, start_time)  # ✅ تاریخ میلادی
            end_dt = dt + timedelta(minutes=service.duration_minutes)
            end_time = end_dt.time()

            # 🔴 بررسی تداخل (با تاریخ میلادی)
            conflict = Appointment.objects.filter(
                appointment_date=new_date_gregorian,  # ✅ تاریخ میلادی
                start_time=start_time
            ).exclude(id=appointment.id).exists()

            if conflict:
                messages.error(
                    request,
                    "در این تاریخ و ساعت قبلاً نوبت ثبت شده است.",
                    extra_tags="panel"
                )
                return redirect("panel:booking_update", booking_id=booking_id)

            # ✅ ذخیره تغییرات (با تاریخ میلادی)
            appointment.appointment_date = new_date_gregorian  # ✅ تاریخ میلادی
            appointment.start_time = start_time
            appointment.end_time = end_time
            appointment.service = service
            appointment.notes = request.POST.get("notes", "")
            appointment.staff_id = staff_id

            # اگر تغییر داشت → برگرده به pending
            appointment.status = "pending"

            appointment.save()

            messages.success(request, "نوبت با موفقیت ویرایش شد.", extra_tags="panel")
            return redirect("panel:booking_list")

    services = Service.objects.all()
    # ✅ دریافت پرسنل‌های فعال مرتبط با خدمت فعلی نوبت
    staff_members = Staff.objects.filter(
        services=appointment.service,
        is_active=True,
        status="active"
    )

   # ✅ به جای آن این کد جدید را قرار دهید:
    jalali_date = jdatetime.date.fromgregorian(date=appointment.appointment_date)
    
    # رشته تاریخ شمسی برای نمایش در فیلد ورودی
    jalali_date_str = f"{jalali_date.year}/{jalali_date.month:02d}/{jalali_date.day:02d}"


    # در تابع booking_update
    today_jalali = jdatetime.date.today()
    jalali_today_str = f"{today_jalali.year}{today_jalali.month:02d}{today_jalali.day:02d}"

    jalali_today_formatted = f"{today_jalali.year}/{today_jalali.month:02d}/{today_jalali.day:02d}"

    # در تابع booking_update
    yesterday_jalali = today_jalali - jdatetime.timedelta(days=1)
    jalali_yesterday_formatted = f"{yesterday_jalali.year}/{yesterday_jalali.month:02d}/{yesterday_jalali.day:02d}"

    yesterday_jalali_str = f"{yesterday_jalali.year}{yesterday_jalali.month:02d}{yesterday_jalali.day:02d}"

    return render(request, "panel/booking_update.html", {
        "appointment": appointment,
        "services": services,
        "staff": staff_members,
        "jalali_date_str": jalali_date_str,
        "jalali_year": jalali_date.year,
        "jalali_month": jalali_date.month,
        "jalali_day": jalali_date.day, 
        "jalali_today_str": jalali_today_str,
        "jalali_today_formatted": jalali_today_formatted, 
        "jalali_yesterday_formatted": jalali_yesterday_formatted,
         "jalali_yesterday_str": yesterday_jalali_str,
    })

@require_POST
@login_required
@panel_access_required
def booking_complete(request, pk):
    if request.method == "POST":
        appointment = get_object_or_404(Appointment, pk=pk, status__in=['pending', 'confirmed'])
        appointment.status = 'completed'
        appointment.save()
        
        messages.success(request, f"نوبت {appointment.user.username} به «انجام شده» تغییر کرد.", extra_tags="panel")
    return redirect('panel:today_appointments')

@require_POST
@login_required
@panel_access_required
def booking_no_show(request, pk):
    if request.method == "POST":
        appointment = get_object_or_404(Appointment, pk=pk, status__in=['pending', 'confirmed'])
        appointment._cancellation_reason = 'no_show'
        appointment.status = 'cancelled'
        appointment.save()
          
        messages.warning(request, f"نوبت {appointment.user.username} به دلیل «عدم حضور» لغو شد.", extra_tags="panel")
    return redirect('panel:today_appointments')


@login_required
@panel_access_required
def today_appointments(request):
    today = date.today()
    appointments = Appointment.objects.filter(
        appointment_date=today,
        status='confirmed'  # فقط نوبت‌های فعال امروز
    ).select_related(
        'user', 'service', 'staff', 'user__profile'
    ).order_by('start_time')
    
    # ✅ محاسبه شماره‌های تماس برای هر نوبت
    appointments_list = []
    for appt in appointments:
        profile_phone = appt.user.profile.phone if hasattr(appt.user, 'profile') else None
        appt_phone = appt.phone
        
        # اگر هر دو وجود دارند و متفاوت هستند
        if profile_phone and appt_phone and profile_phone != appt_phone:
            appt.display_phones = [profile_phone, appt_phone]
        # اگر فقط یکی وجود دارد
        elif profile_phone:
            appt.display_phones = [profile_phone]
        elif appt_phone:
            appt.display_phones = [appt_phone]
        else:
            appt.display_phones = []
        
        appointments_list.append(appt)

# ✅ اضافه کردن صفحه‌بندی
    paginator = Paginator(appointments_list, 10)  # 10 نوبت در هر صفحه
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # تبدیل تاریخ امروز به شمسی برای نمایش
    today_jalali = jdatetime.date.fromgregorian(date=today).strftime('%Y/%m/%d')
    
    return render(request, 'panel/today_appointments.html', {
        'appointments': page_obj,
        'today_jalali': today_jalali,
    })

@login_required
@panel_access_required
def tomorrow_appointments(request):

    tomorrow = date.today() + timedelta(days=1)
    appointments = Appointment.objects.filter(
        appointment_date=tomorrow,
        status__in=['pending', 'confirmed']  # فقط نوبت‌های معتبر
    ).select_related('user', 'service', 'staff', 'user__profile').order_by('start_time')
    
    # ✅ مرتب‌سازی هوشمند: اول نوبت‌های در انتظار، بعد تأیید شده، سپس بر اساس ساعت
    appointments = appointments.order_by(
        '-status',  # pending قبل از confirmed (چون 'p' بعد از 'c' می‌آید)
        'start_time'
    )

    # ✅ محاسبه شماره‌های تماس برای هر نوبت (همان کد بالا)
    appointments_list = []
    for appt in appointments:
        profile_phone = appt.user.profile.phone if hasattr(appt.user, 'profile') else None
        appt_phone = appt.phone
        
        if profile_phone and appt_phone and profile_phone != appt_phone:
            appt.display_phones = [profile_phone, appt_phone]
        elif profile_phone:
            appt.display_phones = [profile_phone]
        elif appt_phone:
            appt.display_phones = [appt_phone]
        else:
            appt.display_phones = []
        
        appointments_list.append(appt)

    # ✅ اضافه کردن صفحه‌بندی
    paginator = Paginator(appointments_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)   

    # تبدیل تاریخ فردا به شمسی
    tomorrow_jalali = jdatetime.date.fromgregorian(date=tomorrow).strftime('%Y/%m/%d')
    
    return render(request, 'panel/tomorrow_appointments.html', {
        'appointments': page_obj,
        'tomorrow_jalali': tomorrow_jalali,
    })


# مدیریت خدمات
# -----------------------------

from django.http import JsonResponse

@login_required
def load_subcategories(request):
    category_id = request.GET.get('category_id')
    subcategories = Subcategory.objects.filter(category_id=category_id).values('id', 'name')
    return JsonResponse(list(subcategories), safe=False)

@login_required
@panel_access_required
def services_list(request):
    category_id = request.GET.get("category")
    subcategory_id = request.GET.get("subcategory")
    services = Service.objects.all()
    
    if category_id:
        services = services.filter(subcategory__category_id=category_id)

    if subcategory_id:
        services = services.filter(subcategory_id=subcategory_id)

    # ✅ اضافه کردن صفحه‌بندی
    paginator = Paginator(services, 15)  # 15 خدمت در هر صفحه (بهینه برای جدول)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = ServiceCategory.objects.all()
    subcategories = Subcategory.objects.filter(
        category_id=category_id
    ) if category_id else Subcategory.objects.none()
    
    return render(request, "panel/services_list.html", {"services": page_obj,
            "categories": categories,
            "subcategories": subcategories,
            "selected_category": category_id,
            "selected_subcategory": subcategory_id,})

@login_required
@panel_access_required
def service_add(request):
    
    GalleryFormSet = modelformset_factory(ServiceImage, form=ServiceGalleryForm, extra=1, can_delete=True)

    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES)

        if form.is_valid() :
            service = form.save()

            for f in request.FILES.getlist('form-0-image'):
                ServiceImage.objects.create(
                    service=service,
                    image=f
                )

            messages.success(request, "خدمت با موفقیت افزوده شد." , extra_tags = "panel")
            return redirect("panel:services_list")
    else:
        form = ServiceForm()

    return render(request, "panel/service_add.html", {
        "form": form,
      
    })

@require_POST
@login_required
@panel_access_required
def service_delete(request, id):
    service = get_object_or_404(Service, id=id)
    service.delete()
    messages.error(request, "سرویس حذف شد." , extra_tags = "panel")
    return redirect("panel:services_list")

@login_required
@panel_access_required
def service_edit(request, id):
    service = get_object_or_404(Service, id=id)

    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES, instance=service)
        
        if form.is_valid() :
            service = form.save()

            for f in request.FILES.getlist('form-0-image'):
                ServiceImage.objects.create(
                    service=service,
                    image=f
                )


            messages.success(request, "خدمت با موفقیت ویرایش شد." , extra_tags = "panel")
            return redirect("panel:services_list")

    else:
        form = ServiceForm(instance=service)

    return render(request, "panel/service_edit.html", {
        "form": form,
        "service": service,
    })

@login_required
@panel_access_required
def delete_service_image(request, image_id):
    image = get_object_or_404(ServiceImage, id=image_id)
    service_id = image.service.id
    image.delete()
    messages.success(request, "عکس با موفقیت حذف شد.", extra_tags="panel")
    
    next_url = request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)

    return redirect("panel:service_edit", id=service_id)

@login_required
@panel_access_required
def category_add(request):
    if request.method == "POST":
        name = request.POST.get("name")

        if name:
            ServiceCategory.objects.create(name=name)
            messages.success(request, "دسته با موفقیت اضافه شد.", extra_tags="panel")
            return redirect("panel:services_list")

    return render(request, "panel/category_add.html")

@login_required
@panel_access_required
def subcategory_add(request):
    categories = ServiceCategory.objects.all()

    if request.method == "POST":
        name = request.POST.get("name")
        category_id = request.POST.get("category")

        if name and category_id:
            Subcategory.objects.create(
                name=name,
                category_id=category_id
            )
            messages.success(request, "زیردسته با موفقیت اضافه شد.", extra_tags="panel")
            return redirect("panel:services_list")

    return render(request, "panel/subcategory_add.html", {
        "categories": categories
    })

@require_POST
@login_required
@panel_access_required
def service_delete_category(request, id):
    category = get_object_or_404(ServiceCategory, id=id)
    if category.subcategories.exists() or Service.objects.filter(subcategory__category=category).exists():
        messages.error(request, "این دسته دارای زیردسته یا خدمت است و قابل حذف نیست.", extra_tags="panel")
    else:
        category.delete()
        messages.success(request, "دسته با موفقیت حذف شد.", extra_tags="panel")
    
    next_url = request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    
    return redirect("panel:services_list")

@require_POST
@login_required
@panel_access_required
def service_delete_subcategory(request, id):
    subcategory = get_object_or_404(Subcategory, id=id)
    if subcategory.services.exists():
        messages.error(request, "این زیردسته دارای خدمت است و قابل حذف نیست.", extra_tags="panel")
    else:
        subcategory.delete()
        messages.success(request, "زیردسته با موفقیت حذف شد.", extra_tags="panel")
    
    next_url = request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)
    
    return redirect("panel:services_list")

@login_required
@panel_access_required
def service_toggle_status(request, pk):
    service = get_object_or_404(Service, pk=pk)

    if request.user.profile.role != "owner":
        return redirect("panel:services_list")

    service.is_active = not service.is_active
    service.save()

    return redirect("panel:services_list")

# مدیریت منشی‌ها
# -----------------------------
@login_required
@panel_access_required
def staff_list(request):
    status_filter = request.GET.get("status")

    personnel = []

    # 👤 مالک + منشی‌ها (از Profile)
    profiles = Profile.objects.filter(
        role__in=["owner", "receptionist"]
    ).select_related("user")

    if status_filter:
        profiles = profiles.filter(status=status_filter)

    for profile in profiles:
        personnel.append({
            "id": profile.user.id,
            "username": profile.user.username,
            "email": profile.user.email,
            "role_label": "مالک" if profile.role == "owner" else "منشی",
            "status": profile.status,
            "is_active": profile.user.is_active,
            "type": "system",
        })

    # 💇‍♀️ پرسنل سالن (Staff)
    staff_members = Staff.objects.all()

    if status_filter:
        staff_members = staff_members.filter(status=status_filter)

    for staff in staff_members:
        personnel.append({
            "id": staff.id,
            "username": staff.full_name,
            "email": "-",
            "phone": staff.phone or "-",
            "role_label": f"پرسنل ({staff.role})",
            "status": staff.status,
            "is_active": staff.is_active,
            "type": "staff",
        })

    can_manage_staff = request.user.profile.role in ["owner", "receptionist"]


    # ✅ اضافه کردن صفحه‌بندی (بعد از ساخت لیست کامل)
    paginator = Paginator(personnel, 12)  # 12 پرسنل در هر صفحه (بهینه برای جدول)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "panel/staff_list.html",
        {"personnel": page_obj,"can_manage_staff": can_manage_staff, "status_filter": status_filter,},
    )

@login_required
@panel_access_required
def staff_add(request):
    if request.method == "POST":
        required_fields = ["username","first_name","last_name","phone","password","confirm_password"]
        for f in required_fields:
            if not request.POST.get(f):
                messages.error(request, f"فیلد {f} نمی‌تواند خالی باشد.", extra_tags="panel")
                return redirect("panel:staff_add")
            
        username = request.POST.get("username")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone = request.POST.get("phone", '').strip()
        
        if phone:
            # اعتبارسنجی شماره موبایل ایران
            if not re.fullmatch(r'09\d{9}', phone):
                messages.error(
                        request,
                        "شماره موبایل باید با 09 شروع شود و دقیقاً 11 رقم باشد.",
                        extra_tags="front"
                    )
                return redirect('panel:staff_add')
        
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "رمز عبور و تکرار آن یکسان نیست.", extra_tags="panel")
            return redirect("panel:staff_add")

        # چک کردن اینکه نام کاربری تکراری نباشد
        if User.objects.filter(username=username).exists():
            messages.error(request, "این نام کاربری قبلاً ثبت شده است." , extra_tags = "panel")
            return redirect("panel:staff_add")

        # ساخت کاربر جدید
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

         # تنظیم پروفایل
        user.profile.phone = phone
        user.profile.status = "active"
        # تعیین نقش در پروفایل
        user.profile.role = "receptionist"
        user.profile.save()

        # تعیین گروه
        group = Group.objects.get(name="receptionist")
        user.groups.add(group)

        # منشی باید دسترسی staff داشته باشد
        user.is_staff = True
        user.save()

        messages.success(request, "منشی با موفقیت اضافه شد." , extra_tags = "panel")
        return redirect("panel:staff_list")  # بعد از ثبت به لیست منشی‌ها می‌رود

    return render(request, "panel/staff_list.html")

@login_required
@panel_access_required
def staff_edit(request, id):
    staff = get_object_or_404(User, id=id)

    if not staff.is_active:
        messages.warning(request, "این پرسنل غیرفعال است و قابل ویرایش نیست" , extra_tags = "panel")
        return redirect("panel:staff_list")


    if request.method == "POST":
        required_fields = ["username","first_name","last_name","phone","password","confirm_password"]
        for f in required_fields:
            if not request.POST.get(f):
                messages.error(request, f"فیلد {f} نمی‌تواند خالی باشد.", extra_tags="panel")
                return redirect("panel:staff_add")
            
        username = request.POST.get("username")
        password = request.POST.get("password")

        # بررسی نام کاربری تکراری
        if User.objects.filter(username=username).exclude(id=staff.id).exists():
            messages.error(request, "این نام کاربری قبلاً ثبت شده است." , extra_tags = "panel")
            return redirect("panel:staff_edit", id=staff.id)

        staff.username = username

        # اگر رمز جدید وارد شده باشد تغییرش می‌دهیم
        if password and password.strip() != "":
            staff.set_password(password)

        staff.save()

        # نقش و گروه اطمینان از reception بودن
        staff.profile.role = "receptionist"
        staff.first_name = request.POST.get("first_name")
        staff.last_name = request.POST.get("last_name")

        staff.profile.phone = request.POST.get("phone")
        staff.profile.status = request.POST.get("status")
        staff.profile.save()

        group = Group.objects.get(name="receptionist")
        staff.groups.clear()
        staff.groups.add(group)

        staff.is_staff = True
        staff.save()

        messages.success(request, "اطلاعات منشی با موفقیت ویرایش شد." , extra_tags = "panel")
        return redirect("panel:staff_list")

    return render(request, "panel/staff_edit.html", {
        "staff": staff,
    })

@require_POST
@login_required
@panel_access_required
def staff_change_status(request, user_id, status):

    # فقط owner اجازه دارد
    if request.user.profile.role not in ["owner", "receptionist"]:
        messages.error(request, "شما اجازه این عملیات را ندارید" , extra_tags = "panel")
        return redirect("panel:staff_list")

    # فقط owner اجازه غیرفعال کردن دارد
    if status == "inactive" and request.user.profile.role != "owner":
        messages.error(
            request,
            "فقط مدیر سالن می‌تواند حساب کاربری را غیرفعال کند",
            extra_tags="panel"
        )
        return redirect("panel:staff_list")

    profile = get_object_or_404(Profile, user_id=user_id)

    if status not in ["active", "inactive", "leave"]:
        messages.error(request, "وضعیت نامعتبر است" , extra_tags = "panel")
        return redirect("panel:staff_list")
    
    # تغییر وضعیت
    profile.status = status
    profile.save()   # 🔥 اینجا sync با User.is_active انجام می‌شود

    # همگام‌سازی با User.is_active
    if status == "inactive":
        profile.user.is_active = False
    else:
        profile.user.is_active = True

    profile.user.save()

    # --------------------
    # 🔔 ساخت اعلان
    # --------------------
    status_labels = {
        "active": "فعال",
        "inactive": "غیرفعال",
        "leave": "مرخصی",
    }

    Notification.objects.create(
        user=profile.user,
        type="status_change",
        channel="email",  # یا sms / whatsapp
        message=f"وضعیت شما توسط مدیر به «{status_labels[status]}» تغییر یافت."
    )


    send_mail(
        subject="تغییر وضعیت حساب کاربری",
        message=f"وضعیت شما به «{status_labels[status]}» تغییر یافت.",
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[profile.user.email],
        fail_silently=True,
    )

    messages.success(request, "وضعیت پرسنل با موفقیت تغییر کرد", extra_tags = "panel")
    return redirect("panel:staff_list")

WEEK_DAYS_FA = [
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه",
    ]

# مدیریت پرسنل سالن
# -----------------------------

@login_required
@panel_access_required
def salon_staff_add(request):
    categories = ServiceCategory.objects.prefetch_related(
        'subcategories__services'
    )

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        role = request.POST.get("role")
        phone = request.POST.get("phone")
        work_days = request.POST.getlist("work_days")
        work_start_time = request.POST.get("work_start_time")
        work_end_time = request.POST.get("work_end_time")
        service_ids = request.POST.getlist("services")
        photo = request.FILES.get("photo")

        # ✅ خدمات جدید - از فیلد مخفی
        services_str = request.POST.get("services", "")
        service_ids = services_str.split(",") if services_str else []

        # ✅ اعتبارسنجی شماره تماس
        if not re.match(r"^09\d{9}$", phone):
            messages.error(
                request,
                "شماره تماس باید ۱۱ رقم باشد و با 09 شروع شود",
                extra_tags="panel"
            )
            return redirect("panel:salon_staff_add")
        
        show_in_about_page = request.POST.get("show_in_about_page") == "on"

        staff = Staff.objects.create(
            full_name=full_name,
            role=role,
            phone=phone,
            photo=photo,
            work_days=work_days,
            work_start_time=work_start_time,
            work_end_time=work_end_time,
            is_active=True,
            status="active",
            show_in_about_page=show_in_about_page
        )

        # ✅ ذخیره خدمات
        if service_ids:
            staff.services.set(service_ids)
        
        staff.save()
        messages.success(request, "پرسنل سالن با موفقیت اضافه شد", extra_tags="panel")
        return redirect("panel:staff_list")

    return render(request, "panel/salon_staff_add.html", {
        "categories": categories,
        "week_days": WEEK_DAYS_FA,
    })

@require_POST
@login_required
@panel_access_required
def salon_staff_change_status(request, staff_id, status):

    if status not in ["active", "inactive", "leave"]:
        messages.error(request, "وضعیت نامعتبر است", extra_tags="panel")
        return redirect("panel:staff_list")

    # فقط owner اجازه غیرفعال کردن دارد
    if status == "inactive" and request.user.profile.role != "owner":
        messages.error(
            request,
            "فقط مدیر سالن می‌تواند حساب کاربری را غیرفعال کند",
            extra_tags="panel"
        )
        return redirect("panel:staff_list")


    staff = get_object_or_404(Staff, id=staff_id)

    staff.status = status

    if status == "inactive":
        staff.is_active = False
    else:
        staff.is_active = True  # active و leave هر دو فعال‌اند

    staff.save()

    messages.success(
        request,
        f"وضعیت پرسنل به «{status}» تغییر کرد",
        extra_tags="panel"
    )

    return redirect("panel:staff_list")

@login_required
@panel_access_required
def salon_staff_edit(request, id):
    staff = get_object_or_404(Staff, id=id)
    categories = ServiceCategory.objects.prefetch_related(
    'subcategories__services'
    )

    if request.method == "POST":
        staff.full_name = request.POST.get("full_name")
        staff.role = request.POST.get("role")
        staff.phone = request.POST.get("phone")
        
        if not re.match(r"^09\d{9}$", staff.phone):
            messages.error(
                request,
                "شماره تماس باید ۱۱ رقم باشد و با 09 شروع شود",
                extra_tags="panel"
            )
            return redirect("panel:salon_staff_edit", id=staff.id)

        # ✅ روزهای کاری (خیلی مهم)
        staff.work_days = request.POST.getlist("work_days")

        # ✅ ساعت کاری
        staff.work_start_time = request.POST.get("work_start_time")
        staff.work_end_time = request.POST.get("work_end_time")

        # ✅ وضعیت
        staff.status = request.POST.get("status")

        # ✅ فعال / غیرفعال
        staff.is_active = "is_active" in request.POST

        # ✅ عکس
        if request.FILES.get("photo"):
            staff.photo = request.FILES.get("photo")
        
        staff.show_in_about_page = request.POST.get("show_in_about_page") == "on"

        staff.save()

         # ✅ خدمات جدید - فقط از فیلد مخفی استفاده کن
        services_str = request.POST.get("services", "")
        service_ids = services_str.split(",") if services_str else []
        
        # ✅ ذخیره خدمات
        if service_ids:
            staff.services.set(service_ids)
        else:
            staff.services.clear()

        messages.success(
            request,
            "اطلاعات پرسنل سالن ویرایش شد",
            extra_tags="panel"
        )
        return redirect("panel:staff_list")

    return render(request, "panel/salon_staff_edit.html", {
        "staff": staff,
        "categories": categories,
        "week_days": WEEK_DAYS_FA,
    })

# پیام‌ها
# -----------------------------

@login_required
@panel_access_required
def messages_manage(request):

    # حذف پیام
    if "delete" in request.GET:
        msg = get_object_or_404(ContactMessage, id=request.GET.get("delete"))
        msg.delete()
        messages.success(request, "پیام حذف شد.",PANEL_TAG = "panel")
        return redirect("panel:messages_manage")

    # علامت‌گذاری پیام به‌عنوان خوانده شده
    if "read" in request.GET:
        msg = get_object_or_404(ContactMessage, id=request.GET.get("read"))
        msg.is_read = True
        msg.save()
        return redirect("panel:messages_manage")

    # نمایش پیام‌ها
    msgs = ContactMessage.objects.all().order_by("-created_at")

    return render(request, "panel/messages.html", {
        "messages_list": msgs
    })

@panel_access_required
def no_access(request):
    return render(request, "panel/no_access.html")

#بخش خدمات پرطرفدار
# -----------------------------
@login_required
@panel_access_required
def popular_services_list(request):
    services = PopularService.objects.all()
    return render(request, 'panel/popular_services_list.html', {
        'services': services
    })

@login_required
@panel_access_required
def popular_service_add(request):
    categories = ServiceCategory.objects.all()

    if request.method == 'POST':
        category = ServiceCategory.objects.get(id=request.POST['category'])

        PopularService.objects.create(
            title=request.POST['title'],
            description=request.POST['description'],
            image=request.FILES['image'],
            category=category,
            order=request.POST.get('order', 0),
            is_active='is_active' in request.POST
        )
        return redirect('panel:popular_services_list')

    return render(request, 'panel/popular_service_form.html',{'categories': categories})

@login_required
@panel_access_required
def popular_service_edit(request, pk):
    service = get_object_or_404(PopularService, pk=pk)
    categories = ServiceCategory.objects.all()

    if request.method == 'POST':
        service.title = request.POST['title']
        service.description = request.POST['description']
        service.category = ServiceCategory.objects.get(id=request.POST['category'])
        service.order = request.POST.get('order', 0)
        service.is_active = 'is_active' in request.POST

        if 'image' in request.FILES:
            service.image = request.FILES['image']

        service.save()
        return redirect('panel:popular_services_list')

    return render(request, 'panel/popular_service_form.html', {
        'service': service,
        'categories': categories
    })

@login_required
@panel_access_required
def popular_service_delete(request, pk):
    service = get_object_or_404(PopularService, pk=pk)
    service.delete()
    return redirect('panel:popular_services_list')

#بخش مقالات
# -----------------------------
@login_required
@panel_access_required
def article_list(request):
    articles = Article.objects.select_related('category', 'author').order_by('-created_at')
    
    # ✅ اضافه کردن صفحه‌بندی
    paginator = Paginator(articles, 12)  # 12 مقاله در هر صفحه
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'panel/article_list.html', {
        'articles': page_obj
    })

@login_required
@panel_access_required
def article_add(request):
    categories = BlogCategory.objects.all()
    service_categories = ServiceCategory.objects.all()
    subcategories = Subcategory.objects.all()
    services = Service.objects.filter(is_active=True)

    if request.method == "POST":
        Article.objects.create(
            title=request.POST['title'],
            content=request.POST['content'],
            image=request.FILES.get('image'),
            category_id=request.POST['category'],
            author=request.user,
            tags=request.POST.get('tags', ''),
            Key_points=request.POST.get('Key_points', ''),
            for_reserve_id=request.POST.get('for_reserve') or None,
            show_on_home = bool(request.POST.get("show_on_home"))
        )
        messages.success(request, "مقاله با موفقیت اضافه شد", extra_tags="panel")
        return redirect('panel:article_list')

    return render(request, 'panel/article_form.html', {
        'categories': categories,
        'services': services,
        'service_categories': service_categories,
        'subcategories': subcategories,
    })

@login_required
@panel_access_required
def article_edit(request, pk):
    article = get_object_or_404(Article, pk=pk)
    categories = BlogCategory.objects.all()
    service_categories = ServiceCategory.objects.all()
    subcategories = Subcategory.objects.all()
    services = Service.objects.filter(is_active=True)

    if request.method == "POST":
        article.title = request.POST['title']
        article.content = request.POST['content']
        article.category_id = request.POST['category']
        article.tags = request.POST.get('tags', '')
        article.Key_points = request.POST.get('Key_points', '')
        article.for_reserve_id = request.POST.get('for_reserve') or None
        article.show_on_home = bool(request.POST.get("show_on_home"))

        if 'image' in request.FILES:
            article.image = request.FILES['image']

        article.save()
        messages.success(request, "مقاله ویرایش شد", extra_tags="panel")
        return redirect('panel:article_list')

    return render(request, 'panel/article_form.html', {
        'article': article,
        'categories': categories,
        'services': services,
         'service_categories': service_categories,
        'subcategories': subcategories,
    })

@require_POST
@login_required
@panel_access_required
def article_delete(request, pk):
    article = get_object_or_404(Article, pk=pk)
    article.delete()
    messages.error(request, "مقاله حذف شد", extra_tags="panel")
    return redirect('panel:article_list')

@login_required
@panel_access_required
def article_category_list(request):
    categories = BlogCategory.objects.all()
    return render(request, 'panel/article_category_list.html', {
        'categories': categories
    })

@login_required
@panel_access_required
def article_category_add(request):
    if request.method == "POST":
        BlogCategory.objects.create(name=request.POST['name'])
        messages.success(request, "دسته‌بندی اضافه شد", extra_tags="panel")
        return redirect('panel:article_category_list')

    return render(request, 'panel/article_category_form.html')

@login_required
@panel_access_required
def article_category_edit(request, pk):
    category = get_object_or_404(BlogCategory, pk=pk)

    if request.method == "POST":
        category.name = request.POST['name']
        category.save()
        messages.success(request, "دسته‌بندی ویرایش شد", extra_tags="panel")
        return redirect('panel:article_category_list')

    return render(request, 'panel/article_category_form.html', {
        'category': category
    })

@require_POST
@login_required
@panel_access_required
def article_category_delete(request, pk):
    category = get_object_or_404(BlogCategory, pk=pk)
    category.delete()
    messages.error(request, "دسته‌بندی حذف شد", extra_tags="panel")
    return redirect('panel:article_category_list')

#بخش نظرات
# -----------------------------
@login_required
@panel_access_required
def panel_review_list(request):
    status = request.GET.get('status', 'all')
    reviews = Review.objects.select_related('user', 'service').order_by('-created_at')
    
    if status == 'approved':
        reviews = reviews.filter(status = 'approved')

    elif status == 'rejected':
        reviews = reviews.filter(status = 'rejected')

    elif status == 'pending':
        reviews = reviews.filter(status = 'pending')
        
    # ✅ اول صفحه‌بندی، بعد پردازش تاریخ شمسی (فقط برای صفحه فعلی)
    paginator = Paginator(reviews, 10)  # 10 نظر در هر صفحه
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ تبدیل تاریخ ایجاد نظر به شمسی (همان روش booking_list)
    for review in page_obj:
        # تبدیل به زمان محلی پروژه (برای جلوگیری از اختلاف تاریخ)
        local_time = timezone.localtime(review.created_at)
        # تبدیل به تاریخ شمسی
        jalali_dt = jdatetime.datetime.fromgregorian(datetime=local_time)
        # ذخیره فرمت شمسی در خود المان برای استفاده در تمپلیت
        review.jalali_date_str = jalali_dt.strftime('%Y/%m/%d')
        review.jalali_time_str = jalali_dt.strftime('%H:%M')  # زمان هم شمسی (اختیاری اما پیشنهادی)

    return render(request, 'panel/review_list.html', {
        'reviews': page_obj,
        'status': status
    })

@require_POST
@login_required
@panel_access_required
def review_approve(request, pk):
    review = get_object_or_404(Review, pk=pk)
    old_status = review.status
    
    # ⛔ اگر قبلاً تأیید شده
    if review.status == 'approved':
        messages.info(request, 'این نظر قبلاً تأیید شده است.', extra_tags='panel')
        return redirect('panel:review_list')
    
    review.status = 'approved'
    review.save(update_fields=['status'])
    messages.success(request, 'نظر تأیید شد', extra_tags='panel')
    
    # ✅ ارسال ایمیل به کاربر
    email_sent = False
    if review.user and review.user.email:
        try:
             # ✅ بررسی ایمن وجود سرویس
            service_name = review.service.name if review.service else "خدمات سالن"
            
            subject = 'نظر شما تأیید شد ✅'
            message = f"""سلام {review.user.get_full_name() or review.user.username} عزیز،

نظر شما برای خدمت «{service_name}» در سالن زیبایی نورا تأیید شد و به زودی در سایت نمایش داده خواهد شد.

از اینکه وقت خود را برای اشتراک‌گذاری نظرتان گذاشتید، سپاسگزاریم.

با احترام،
تیم سالن زیبایی نورا
"""
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [review.user.email],
                fail_silently=False,
            )
            email_sent = True
            logger.info(f"ایمیل تأیید نظر به {review.user.email} برای نظر #{review.id} ارسال شد")
        except Exception as e:
            logger.error(f"خطا در ارسال ایمیل تأیید نظر به {review.user.email}: {str(e)}")
    
    # ✅ نمایش پیام مناسب به مدیر
  #  if email_sent:
   #     messages.success(request, f'نظر تأیید شد و ایمیل به {review.user.username} ارسال گردید ✉️', extra_tags='panel')
    #elif review.user.email:
     #   messages.warning(request, f'نظر تأیید شد اما ارسال ایمیل به {review.user.username} با خطا مواجه شد!', extra_tags='panel')
  #  else:
   #     messages.info(request, f'نظر تأیید شد (کاربر {review.user.username} ایمیل ندارد)', extra_tags='panel')
     
    return redirect('panel:review_list')

@require_POST
@login_required
@panel_access_required
def review_reject(request, pk):
    review = get_object_or_404(Review, pk=pk)
    old_status = review.status
    
     # ⛔ اگر قبلاً رد شده
    if review.status == 'rejected':
        messages.info(request, 'این نظر قبلاً رد شده است.', extra_tags='panel')
        return redirect('panel:review_list')
    
    review.status = 'rejected'
    review.save(update_fields=['status'])
    messages.warning(request, 'نظر رد شد', extra_tags='panel')
    
     # ✅ ارسال ایمیل به کاربر
    email_sent = False
    if review.user and review.user.email:
        try:
            # ✅ بررسی ایمن وجود سرویس
            service_name = review.service.name if review.service else "خدمات سالن"
            
            subject = 'نظر شما بررسی شد ❌'
            message = f"""سلام {review.user.get_full_name() or review.user.username} عزیز،

با تشکر از نظر ارزشمند شما برای خدمت «{service_name}»، 
متأسفانه نظر شما مطابق با سیاست‌های سایت نبود و پس از بررسی، قابل نمایش نیست.

هرگونه پیشنهاد یا انتقاد دیگری دارید، خوشحال می‌شویم در پنل کاربری یا از طریق تماس با ما با ما در میان بگذارید.

با احترام،
تیم سالن زیبایی نورا
"""
            send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [review.user.email],
                    fail_silently=False,
                )
            email_sent = True
            logger.info(f"ایمیل رد نظر به {review.user.email} برای نظر #{review.id} ارسال شد")
        except Exception as e:
            logger.error(f"خطا در ارسال ایمیل رد نظر به {review.user.email}: {str(e)}")
    
    # ✅ نمایش پیام مناسب به مدیر
#    if email_sent:
 #       messages.success(request, f'نظر رد شد و ایمیل به {review.user.username} ارسال گردید ✉️', extra_tags='panel')
  #  elif review.user.email:
   #     messages.warning(request, f'نظر رد شد اما ارسال ایمیل به {review.user.username} با خطا مواجه شد!', extra_tags='panel')
    #else:
     #   messages.info(request, f'نظر رد شد (کاربر {review.user.username} ایمیل ندارد)', extra_tags='panel')
        
    return redirect('panel:review_list')

@login_required
@panel_access_required
def review_reply(request, pk):
    review = get_object_or_404(Review, pk=pk)

    if request.method == "POST":
        reply = request.POST.get("admin_reply", "").strip()

        if reply:
            review.admin_reply = reply
            review.save()
            messages.success(request, "پاسخ ثبت شد", extra_tags="panel")
        else:
            messages.error(request, "پاسخ نمی‌تواند خالی باشد", extra_tags="panel")

    Notification.objects.create(
        user=review.user,
        message="پاسخی برای نظر شما ثبت شد."
    )


    return redirect("panel:review_list")

#کد تخفیف
# -----------------------------
def to_jalali(date):
    if not date:
        return ""
    return jdatetime.date.fromgregorian(date=date).strftime('%Y/%m/%d')

@login_required
@panel_access_required
def discount_codes(request):
    # فقط برای مالک یا منشی نشون بده
    if request.user.profile.role not in ["owner", "receptionist"]:
        return redirect("panel:dashboard")

    if request.method == "POST":
        if "delete_id" in request.POST:
            DiscountCode.objects.filter(id=request.POST["delete_id"]).delete()
            return redirect("panel:discount_codes")

        if "toggle_active" in request.POST:
            code_id = request.POST["toggle_active"]
            code = DiscountCode.objects.get(id=code_id)
            code.is_active = not code.is_active
            code.save()

                # وقتی فعال شد اعلان بفرست
            if code.is_active and not code.notification_sent:
                code.notification_sent = True
                code.save()

                target_users = User.objects.filter(is_active=True)

                # ❗ اعلان‌های قبلی این کد تخفیف حذف شود
                Notification.objects.filter(discount=code).delete()

                notifications = [
                    Notification(
                        user=u,
                        discount=code,
                        type="promotion",
                        channel="email",
                        status="pending",
                        message=(
                            f'کد تخفیف «{code.code}» ({code.percent}٪) '
                            f'تا {to_jalali(code.expires_at)} معتبر است.{code.extra_message}'
                        ),
                    )
                    for u in target_users
                ]
                Notification.objects.bulk_create(notifications)

                subject = f'کد تخفیف جدید: {code.code}'
                body_tpl = (
                    "سلام {username},\n\n"
                    "کد تخفیف {code} ({percent}٪) تا {expires} معتبر است.\n\n"
                    "{extra}\n"
                    "موفق باشید!"
                )
                for user in target_users:
                    if not user.email:
                        continue
                    body = body_tpl.format(
                        username=user.username,
                        code=code.code,
                        percent=code.percent,
                        expires=to_jalali(code.expires_at),
                        extra=code.extra_message,  
                    )
                    try:
                        send_mail(
                            subject, body, None, [user.email], fail_silently=False
                        )
                        Notification.objects.filter(
                            user=user, discount=code
                        ).update(status="sent", sent_at=timezone.now())
                    except Exception as e:
                        logger.warning(f"ارسال ایمیل به {user.email} شکست: {e}")

                return redirect("panel:discount_codes")
        # **ارسال دوباره اعلان**
        if "resend_notify" in request.POST:
            code = DiscountCode.objects.get(id=request.POST["resend_notify"])
            code.notification_sent = True
            code.save()
            
            Notification.objects.filter(discount=code).delete()

            target_users = User.objects.filter(is_active=True)

            notifications = [
                    Notification(
                        user=u,
                        discount=code,
                        type="promotion",
                        channel="email",
                        status="pending",
                        message=(
                            f'کد تخفیف «{code.code}» ({code.percent}٪) '
                            f'تا {to_jalali(code.expires_at)} معتبر است.{code.extra_message}'
                        ),
                    )
                    for u in target_users
                ]
            Notification.objects.bulk_create(notifications)

            subject = f'کد تخفیف جدید: {code.code}'
            body_tpl = (
                    "سلام {username},\n\n"
                    "کد تخفیف {code} ({percent}٪) تا {expires} معتبر است.\n\n"
                    "موفق باشید!"
                )
            for user in target_users:
                if not user.email:
                    continue
                body = body_tpl.format(
                        username=user.username,
                        code=code.code,
                        percent=code.percent,
                        expires=to_jalali(code.expires_at),
                    )
                try:
                    send_mail(
                            subject, body, None, [user.email], fail_silently=False
                        )
                    Notification.objects.filter(
                            user=user, discount=code
                        ).update(status="sent", sent_at=timezone.now())
                except Exception as e:
                    logger.warning(f"ارسال ایمیل به {user.email} شکست: {e}")

            return redirect("panel:discount_codes")
        
    # جستجو
    query = request.GET.get("search", "")
    if query:
        codes = DiscountCode.objects.filter(code__icontains=query)
    else:
        codes = DiscountCode.objects.all().order_by('-id')

    # ✅ اضافه کردن صفحه‌بندی (فقط این بخش جدید است)
    paginator = Paginator(codes, 10)  # 10 کد در هر صفحه
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "panel/discount_codes.html", {
        "codes": page_obj,
        "query": query,
    })


User = get_user_model()

@login_required
@panel_access_required
def discount_code_create(request):
    if request.method == "POST":
        form = DiscountCodeForm(request.POST)
        if form.is_valid():
            discount = form.save(commit=False)   # نهایی‌سازی نکن
            discount.user = request.user 
            # ⬇️  قبل از ذخیره‌سازی فیلد اعلان را علامت بزنید
            # فقط وقتی فعال است اعلان می‌فرستیم
            if discount.is_active:
                discount.notification_sent = True
                        # اضافه کردن کاربر
                discount.save()
            
                # ---- کاربران هدف را انتخاب کنید ----
                # مثال: همه کاربران فعال یا فیلتر دلخواه
                target_users = User.objects.filter(is_active=True)

                # ---- اعلان برای هر کاربر ----
                # ایجاد اعلان‌ها
                notifications = [
                    Notification(
                        user=u,
                        discount=discount,   
                        type="promotion",                # مقدار الزامی
                        channel="email", 
                        status='pending',
                        message=(
                            f'کد تخفیف «{discount.code}» ({discount.percent}٪) '
                            f'تا {to_jalali(discount.expires_at)} معتبر است.{discount.extra_message}'
                        ),
                    )
                    for u in target_users
                ]
                Notification.objects.bulk_create(notifications)

                # ارسال ایمیل به هر کاربر
                subject = f'کد تخفیف جدید: {discount.code}'
                body_template = (
                    "سلام {username},\n\n"
                    "کد تخفیف {code} ({percent}٪) تا {expires} معتبر است.\n\n"
                    "{extra}\n"
                    "موفق باشید!"
                )
                for user in target_users:
                    if not user.email:
                        continue

                    body = body_template.format(
                        username=user.username,
                        code=discount.code,
                        percent=discount.percent,
                        expires=to_jalali(discount.expires_at),
                        extra=discount.extra_message,  
                    )
                    try:
                        send_mail(
                            subject,
                            body,
                            None,               # from DEFAULT_FROM_EMAIL
                            [user.email],
                            fail_silently=False,
                        )
                        # به‌روزرسانی فیلد sent_mail
                        Notification.objects.filter(user=user, discount_id=discount.id,).update(status="sent", sent_at=timezone.now())
                    except Exception as e:          # شامل TimeoutError، BadHeaderError و غیره
                        # فقط لاگ می‌کنیم؛ عملیات اصلی (ساخت کد) خراب نمی‌شود
                        logger.warning(
                            f"ارسال ایمیل به {user.email} شکست: {e}"
                        )
                        # وضعیت اعلان به pending می‌ماند تا بعداً بررسی شود
                        continue
                messages.success(request, "کد تخفیف با موفقیت ثبت شد و اعلان برای کاربران ارسال شد.")
            else:
                # غیر فعال → فقط ذخیره می‌کنیم
                discount.notification_sent = False
                discount.save()
                messages.success(request, "کد تخفیف غیر فعال ثبت شد.")

            return redirect("panel:discount_codes")
        return render(request, "panel/discount_code_form.html", {"form": form})
    else:           # GET
        form = DiscountCodeForm()
    return render(request, "panel/discount_code_form.html", {"form": form})

@login_required
@panel_access_required
def discount_code_edit(request, pk):
    code = get_object_or_404(DiscountCode, pk=pk)
    if request.method == "POST":
        form = DiscountCodeForm(request.POST, instance=code)
        if form.is_valid():
            discount = form.save(commit=False)   # نهایی‌سازی نکن
            discount.user = request.user  
            # اگر هنوز اعلان برای این کد تنظیم نشده باشد:
              # اگر وضعیت فعال شد و قبلاً اعلان ندیده باشد
            if discount.is_active and not discount.notification_sent:
                discount.notification_sent = True

                    # اضافه کردن کاربر
                discount.save()
                # ---- کاربران هدف را انتخاب کنید ----
                # مثال: همه کاربران فعال یا فیلتر دلخواه
                target_users = User.objects.filter(is_active=True)

                # ---- اعلان برای هر کاربر ----
                # اعلان‌ها (همان منطق بالا)
                notifications = [
                    Notification(
                        user=u,
                        discount=discount,
                        type="promotion",
                        channel="email",
                        status='pending',
                        message=(
                            f'کد تخفیف «{discount.code}» ({discount.percent}٪) '
                            f'تا {to_jalali(discount.expires_at)} معتبر است.{discount.extra_message}'
                        ),
                    )
                    for u in target_users
                ]
                Notification.objects.bulk_create(notifications)

                # ---------- ارسال ایمیل ----------
                subject = f'کد تخفیف جدید: {discount.code}'
                body_template = (
                    "سلام {username},\n\n"
                    "کد تخفیف {code} ({percent}٪) تا {expires} معتبر است.\n\n"
                    "{extra}\n"
                    "موفق باشید!"
                )
                for user in target_users:
                    if not user.email:
                        continue
                    body = body_template.format(
                        username=user.username,
                        code=discount.code,
                        percent=discount.percent,
                        expires=to_jalali(discount.expires_at),
                        extra=discount.extra_message,  
                    )
                    try:
                        send_mail(
                            subject,
                            body,
                            None,                 # استفاده از DEFAULT_FROM_EMAIL
                            [user.email],
                            fail_silently=False,
                        )
                        # وضعیت اعلان را به «sent» بروز می‑کنیم
                        Notification.objects.filter(
                            user=user,
                            discount_id=discount.id,
                        ).update(status="sent", sent_at=timezone.now())
                    
                    except Exception as exc:
                        logger.warning(
                            f"ارسال ایمیل به {user.email} شکست: {exc}"
                        )
                        # حالت pending می‌ماند تا بعداً بررسی شود

                messages.success(request, "کد تخفیف با موفقیت ثبت شد و اعلان برای کاربران ارسال شد.")
            else:
                # غیرفعال یا قبلاً اعلان ارسال شده → فقط ذخیره
                discount.save()
                messages.success(request, "کد تخفیف به‌روز شد.")
            return redirect("panel:discount_codes")
    else:
        form = DiscountCodeForm(instance=code)
    return render(request, "panel/discount_code_form.html", {"form": form, "code": code})

#تعطیلات
# -----------------------------
@login_required
@panel_access_required
def holiday_list(request):
    holidays = Holiday.objects.all().order_by('-date')
    
    # 📅 گرفتن ماه و سال جاری شمسی
    today = jdatetime.date.today()
    current_year = today.year
    current_month = today.month

    # روزهای تعطیل این ماه
    month_holidays_days = []
    for holiday in holidays:
        if holiday.jalali_date and holiday.is_active:
            try:
                h_year, h_month, h_day = map(int, holiday.jalali_date.split('/'))
                if h_year == current_year and h_month == current_month:
                    month_holidays_days.append(h_day)
            except:
                pass

    # برای هر تعطیلی، مطمئن شویم jalali_date وجود دارد
    for holiday in holidays:
        if not holiday.jalali_date:
            try:
                # تبدیل تاریخ میلادی به شمسی
                jalali_date = jdatetime.date.fromgregorian(date=holiday.date)
                holiday.jalali_date = jalali_date.strftime('%Y/%m/%d')
                holiday.save()
            except:
                holiday.jalali_date = "نامعتبر"

    # فیلتر بر اساس نوع
    holiday_type = request.GET.get('type')
    if holiday_type:
        holidays = holidays.filter(holiday_type=holiday_type)
    
    # فیلتر بر اساس وضعیت فعال/غیرفعال
    is_active = request.GET.get('is_active')
    if is_active:
        holidays = holidays.filter(is_active=(is_active == 'true'))
    
    # ✅ اضافه کردن صفحه‌بندی (فقط این بخش جدید است)
    paginator = Paginator(holidays, 10)  # 10 تعطیلی در هر صفحه
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'panel/holiday_list.html', {
        'holidays': page_obj,
        'current_year': current_year,
        'current_month': current_month,
        'month_holidays_days': month_holidays_days,
    })

@login_required
@panel_access_required
def holiday_create(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')  # فرمت: 1404/02/15
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        holiday_type = request.POST.get('holiday_type', 'custom')
        is_active = request.POST.get('is_active') == 'on'
        is_half_day = request.POST.get('is_half_day') == 'on'
        half_day_period = request.POST.get('half_day_period', '')
        
        try:
            # تبدیل تاریخ شمسی به میلادی
            year, month, day = map(int, date_str.split('/'))
            jalali_date = jdatetime.date(year, month, day)
            gregorian_date = jalali_date.togregorian()
            
            # ✅ اضافه کردن jalali_date_str برای ذخیره‌سازی
            jalali_date_str = f"{year}/{month:02d}/{day:02d}"  # نرمال‌سازی فرمت
    
            # ایجاد تعطیلی جدید
            Holiday.objects.create(
                date=gregorian_date,
                title=title,
                jalali_date=jalali_date_str,
                description=description,
                holiday_type=holiday_type,
                is_active=is_active,
                is_half_day=is_half_day,
                half_day_period=half_day_period if is_half_day else None
            )
            
            messages.success(request, "تعطیلی با موفقیت اضافه شد", extra_tags="panel")
            return redirect('panel:holiday_list')
            
        except Exception as e:
            messages.error(request, f"خطا در ایجاد تعطیلی: {str(e)}", extra_tags="panel")
    
    return render(request, 'panel/holiday_form.html')

@login_required
@panel_access_required
def holiday_edit(request, pk):
    holiday = get_object_or_404(Holiday, pk=pk)
    
    if request.method == 'POST':
        date_str = request.POST.get('date')
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        holiday_type = request.POST.get('holiday_type', 'custom')
        is_active = request.POST.get('is_active') == 'on'
        is_half_day = request.POST.get('is_half_day') == 'on'
        half_day_period = request.POST.get('half_day_period', '')
        
        try:
            # تبدیل تاریخ شمسی به میلادی
            year, month, day = map(int, date_str.split('/'))
            jalali_date = jdatetime.date(year, month, day)
            gregorian_date = jalali_date.togregorian()
            
            # ✅ اضافه کردن jalali_date_str
            jalali_date_str = f"{year}/{month:02d}/{day:02d}"
            

            # بروزرسانی تعطیلی
            holiday.date = gregorian_date
            holiday.jalali_date = jalali_date_str
            holiday.title = title
            holiday.description = description
            holiday.holiday_type = holiday_type
            holiday.is_active = is_active
            holiday.is_half_day = is_half_day
            holiday.half_day_period = half_day_period if is_half_day else None
            holiday.save()
            
            messages.success(request, "تعطیلی با موفقیت ویرایش شد", extra_tags="panel")
            return redirect('panel:holiday_list')
            
        except Exception as e:
            messages.error(request, f"خطا در ویرایش تعطیلی: {str(e)}", extra_tags="panel")
    
    # تبدیل تاریخ میلادی به شمسی برای نمایش در فرم
    jalali_date = jdatetime.date.fromgregorian(date=holiday.date)
    jalali_date_str = jalali_date.strftime('%Y/%m/%d')
    
    return render(request, 'panel/holiday_form.html', {
        'holiday': holiday,
        'jalali_date_str': jalali_date_str,
    })

@require_POST
@login_required
@panel_access_required
def holiday_delete(request, pk):
    holiday = get_object_or_404(Holiday, pk=pk)
    holiday.delete()
    messages.success(request, "تعطیلی با موفقیت حذف شد", extra_tags="panel")
    return redirect('panel:holiday_list')

@require_POST
@login_required
@panel_access_required
def holiday_toggle_active(request, pk):
    holiday = get_object_or_404(Holiday, pk=pk)
    holiday.is_active = not holiday.is_active
    holiday.save()
    status = "فعال" if holiday.is_active else "غیرفعال"
    messages.success(request, f"تعطیلی {status} شد", extra_tags="panel")
    return redirect('panel:holiday_list')

#تنظیمات سالن
# -----------------------------
@login_required
@panel_access_required
def salon_settings(request):
    # فقط مالک دسترسی داشته باشد
    if request.user.profile.role not in ["owner", "receptionist"]:
        messages.error(request, "شما مجوز دسترسی ندارید" , extra_tags="panel")
        return redirect('panel:dashboard')
    
    settings, created = SalonSettings.objects.get_or_create(id=1)
    
    # ✅ تعیین حالت فقط-خواندنی برای منشی
    is_read_only = (request.user.profile.role == "receptionist")
    

    if request.method == 'POST':
        if request.user.profile.role != "owner":
            messages.error(request, "فقط مالک سالن می‌تواند تنظیمات را ویرایش کند", extra_tags="panel")
            return redirect('panel:salon_settings')

        settings.salon_name = request.POST.get('salon_name', '')
        settings.phone = request.POST.get('phone', '')
        settings.open_time = request.POST.get('open_time', '09:00')
        settings.close_time = request.POST.get('close_time', '18:00')
        settings.has_salon_lunch_break = request.POST.get('has_salon_lunch_break') == 'on'
        settings.salon_lunch_start = request.POST.get('salon_lunch_start', '13:00')
        settings.salon_lunch_end = request.POST.get('salon_lunch_end','14:00')
        settings.whatsapp = request.POST.get('whatsapp', '').strip()
        settings.enable_online_payment = request.POST.get('enable_online_payment') == 'on'
        settings.global_duration_note = request.POST.get('global_duration_note', '').strip()
        settings.global_price_note = request.POST.get('global_price_note', '').strip()

        settings.save()
        messages.success(request, "تنظیمات ذخیره شد", extra_tags="panel")
        return redirect('panel:salon_settings')
    
    return render(request, 'panel/salon_settings.html', {'settings': settings , 'is_read_only': is_read_only})


#پکیج ها-پیشنهاد های ویژه
# -----------------------------

# لیست پکیج‌ها
@login_required
@panel_access_required
def package_list(request):
    packages = Package.objects.all().prefetch_related('service').order_by('-created_at')
    
    # ✅ اضافه کردن صفحه‌بندی
    paginator = Paginator(packages, 10)  # 10 پکیج در هر صفحه
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'panel/package_list.html', {
        'packages': page_obj
    })

# افزودن پکیج جدید
@login_required
@panel_access_required
def package_add(request):    
    categories = ServiceCategory.objects.all()  # دریافت تمام دسته‌بندی‌ها

    if request.method == 'POST':
        package = Package()
        package.title = request.POST.get('title')
        package.description = request.POST.get('description')
        package.original_price = request.POST.get('original_price') or None
        package.discounted_price = request.POST.get('discounted_price')
        package.discount_badge = request.POST.get('discount_badge', '')
        package.is_active = 'is_active' in request.POST
        
        # ✅ این بخش جدید را اضافه کنید
        if 'is_limited_time' in request.POST:
            package.is_limited_time = True
            package.duration_days = request.POST.get('duration_days', 3)
            
            # دریافت زمان شروع از فرم
            start_time_str = request.POST.get('start_time')

            if start_time_str:
                try:
                    package.start_time = timezone.make_aware(
                        datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
                    )
                except ValueError:
                    # اگر مقدار نامعتبر بود (مثلاً Invalid date)
                    package.start_time = timezone.now()
            else:
                package.start_time = timezone.now()
                
        else:
            package.is_limited_time = False
            package.start_time = None
        
        # ذخیره عکس
        if 'image' in request.FILES:
            package.image = request.FILES['image']
        
        # در تابع package_add (بعد از package.is_active = ...)
        package.show_on_homepage = request.POST.get('show_on_homepage') == '1'

        package.save()
                
        # ✅ فقط اگر پکیج فعاله اعلان بفرست
        if package.is_active:
            send_package_notification(package)

         # ارتباط با خدمت
        service_ids = request.POST.getlist('services[]')

        if service_ids:
            services = Service.objects.filter(id=service_ids)
            package.service.set(services)

        messages.success(request, "پکیج با موفقیت اضافه شد", extra_tags="panel")
        return redirect('panel:package_list')
    
    return render(request, 'panel/package_form.html', {
        'categories': categories,
        'action': 'add'
    })

# ویرایش پکیج
@login_required
@panel_access_required
def package_edit(request, pk):
    package = get_object_or_404(Package, pk=pk)
    categories = ServiceCategory.objects.all()  # دریافت تمام دسته‌بندی‌ها

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "لطفاً عنوان پکیج را وارد کنید", extra_tags="panel")
            return redirect('panel:package_edit', pk=pk)
            
        package.title = title
        
        package.description = request.POST.get('description')
        package.original_price = request.POST.get('original_price') or None
        package.discounted_price = request.POST.get('discounted_price')
        package.discount_badge = request.POST.get('discount_badge', '')
        package.is_active = 'is_active' in request.POST
        
        # ✅ این بخش جدید را اضافه کنید
        if 'is_limited_time' in request.POST:
            package.is_limited_time = True
            package.duration_days = request.POST.get('duration_days', 3)
            
            # دریافت زمان شروع از فرم
            start_time_str = request.POST.get('start_time')

            if start_time_str:
                try:
                    package.start_time = timezone.make_aware(
                        datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
                    )
                except ValueError:
                    # اگر مقدار نامعتبر بود (مثلاً Invalid date)
                    package.start_time = timezone.now()
            else:
                package.start_time = timezone.now()
                
        else:
            package.is_limited_time = False
            package.start_time = None

        # ذخیره عکس جدید
        if 'image' in request.FILES:
            package.image = request.FILES['image']
        
        # در تابع package_edit (بعد از package.is_active = ...)
        package.show_on_homepage = request.POST.get('show_on_homepage') == '1'

        package.save()
        
        # ارتباط با خدمت
        service_ids = request.POST.getlist('services[]')
        
        print(request.POST.getlist('services[]'))
    
        if service_ids:
            services = Service.objects.filter(id__in=service_ids)
            package.service.set(services)
        else:
            package.service.clear()
            
        messages.success(request, "پکیج با موفقیت ویرایش شد", extra_tags="panel")
        return redirect('panel:package_list')
    
    return render(request, 'panel/package_form.html', {
        'package': package,
        'categories': categories,
        'action': 'edit'
    })

# حذف پکیج
@require_POST
@login_required
@panel_access_required
def package_delete(request, pk):

    package = get_object_or_404(Package, pk=pk)
    package.delete()
    messages.success(request, "پکیج با موفقیت حذف شد", extra_tags="panel")
    return redirect('panel:package_list')


User = get_user_model()

def send_package_notification(package):
    users = User.objects.filter(is_active=True)

    subject = f"🎁 یک پیشنهاد ویژه فقط برای شما | {package.title}"

    message = f"""
    سلام 🌸

    یه خبر خوب برات داریم!

    پکیج جدید «{package.title}» به مجموعه ما اضافه شده 👇  
    ✨ ترکیبی از خدمات محبوب  
    💎 با قیمتی ویژه و محدود

    💰 قیمت پکیج: {package.discounted_price} تومان

    اگر دنبال یه تغییر جذاب یا رسیدگی حرفه‌ای به خودتی،
    این پکیج دقیقاً همونه که دنبالش بودی 😉

    منتظرت هستیم 💖  
    تیم سالن زیبایی
    """


    # ---------- ارسال ایمیل ----------
    email_messages = []
    for user in users:
        if user.email:
            email_messages.append((
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            ))

    if email_messages:
        send_mass_mail(email_messages, fail_silently=True)

    for user in users:
        Notification.objects.create(
            user=user,
            type='promotion',          # از TYPE_CHOICES
            channel='email',           # یا sms / whatsapp
            message=f"🎁 پکیج جدید: {package.title} با قیمت ویژه منتشر شد",
            status='sent'
        )

@require_POST
@login_required
@panel_access_required
def package_resend_notification(request, pk):
    package = get_object_or_404(Package, pk=pk)

    send_package_notification(package)

    messages.success(request, "اعلان و ایمیل مجدد ارسال شد ✅", extra_tags="panel")
    return redirect('panel:package_list')


#مدیریت پرداخت‌ها
# -----------------------------
@login_required
@panel_access_required
def payment_list(request):
    payments = Payment.objects.select_related(
        "appointment",
        "appointment__user",
        "appointment__service",
        "appointment__package_booking",
        "appointment__package_booking__package",
    ).all().order_by("-paid_at")

    payment_method = request.GET.get("method")
    status = request.GET.get("status")

    if payment_method:
        payments = payments.filter(payment_method=payment_method)

    if status:
        payments = payments.filter(status=status)

    # ✅ اول صفحه‌بندی، بعد پردازش تاریخ (فقط برای صفحه فعلی - بهینه‌سازی حیاتی!)
    paginator = Paginator(payments, 10)  # 10 پرداخت در هر صفحه
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # ✅ تبدیل تاریخ پرداخت به شمسی
    for payment in page_obj:
        if payment.paid_at:
            local_time = timezone.localtime(payment.paid_at)
            jalali = jdatetime.datetime.fromgregorian(datetime=local_time)
            payment.paid_at_jalali = jalali.strftime("%Y/%m/%d - %H:%M")
        else:
            payment.paid_at_jalali = "-"

    context = {
        "payments": page_obj,
        "selected_method": payment_method,
        "selected_status": status,
    }

    return render(request, "panel/payment_list.html", context)


#گزارش درامد
from django.db.models import Sum, Q
from django.utils import timezone
from booking.models import Payment, PackagePayment , Staff
from datetime import datetime , timedelta
from django.db.models import Count
from django.db.models import F

@panel_access_required
def income_report(request):

    payments = Payment.objects.filter(status='success')
    package_payments = PackagePayment.objects.filter(status='success')

    today = timezone.localdate()

    # 📌 فیلترهای سریع
    filter_type = request.GET.get('filter')

    if filter_type == 'today':
        payments = payments.filter(paid_at__date=today)
        package_payments = package_payments.filter(created_at__date=today)

    elif filter_type == 'week':
        start_week = today - timedelta(days=today.weekday())
        payments = payments.filter(paid_at__date__gte=start_week)
        package_payments = package_payments.filter(created_at__date__gte=start_week)

    elif filter_type == 'month':
        payments = payments.filter(
            paid_at__year=today.year,
            paid_at__month=today.month
        )
        package_payments = package_payments.filter(
            created_at__year=today.year,
            created_at__month=today.month
        )

    elif filter_type == 'year':
        payments = payments.filter(paid_at__year=today.year)
        package_payments = package_payments.filter(created_at__year=today.year)

    # 📅 بازه دلخواه
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        payments = payments.filter(paid_at__date__gte=start_date)
        package_payments = package_payments.filter(created_at__date__gte=start_date)

    if end_date:
        payments = payments.filter(paid_at__date__lte=end_date)
        package_payments = package_payments.filter(created_at__date__lte=end_date)

    # 👩‍🔧 فیلتر پرسنل
    staff_id = request.GET.get('staff')
    if staff_id:
        payments = payments.filter(appointment__staff_id=staff_id)
        package_payments = package_payments.filter(appointment__staff_id=staff_id)

    # 💳 فیلتر روش پرداخت
    payment_method = request.GET.get('method')
    if payment_method:
        payments = payments.filter(payment_method=payment_method)

    top_service = payments.values(
        service_name=F('appointment__service__name')
    ).annotate(
        total_sales=Count('id'),
        total_income=Sum('amount')
    ).order_by('-total_sales').first()


    # 💰 محاسبه درآمد
    services_income = payments.aggregate(total=Sum('amount'))['total'] or 0
    packages_income = package_payments.aggregate(total=Sum('amount'))['total'] or 0
    total_income = services_income + packages_income

    top_staff = payments.values(
        'appointment__staff__full_name'
    ).annotate(
        total_income=Sum('amount')
    ).order_by('-total_income')

    online_income = payments.filter(payment_method='online').aggregate(total=Sum('amount'))['total'] or 0
    cash_income = payments.filter(payment_method='cash').aggregate(total=Sum('amount'))['total'] or 0
    card_income = payments.filter(payment_method='card').aggregate(total=Sum('amount'))['total'] or 0

    total_payment_income = online_income + cash_income + card_income


    context = {
        'total_income': total_income,
        'services_income': services_income,
        'packages_income': packages_income,
        'staffs': Staff.objects.all(),
        'selected_staff': staff_id,
        'selected_method': payment_method,
        'filter_type': filter_type,
        'top_service': top_service,
        'top_staff': top_staff[:5],
        'online_income': online_income,
        'cash_income': cash_income,
        'card_income': card_income,
        'total_payment_income': total_payment_income,

    }

    return render(request, 'panel/income_report.html', context)


from django.shortcuts import get_object_or_404
from booking.models import Staff, Appointment
from django.utils import timezone

@panel_access_required
def staff_plan(request):

    staffs = Staff.objects.filter(is_active=True)

    staff_id = request.GET.get("staff")

    staff = None
    appointments = None
    today = timezone.localdate()

    if staff_id:
        staff = get_object_or_404(Staff, id=staff_id)

        appointments = Appointment.objects.filter(
            staff=staff,
            appointment_date=today
        ).order_by('start_time')

    context = {
        "staffs": staffs,
        "staff": staff,
        "appointments": appointments,
        "today": today,
        "selected_staff": staff_id,
    }

    return render(request, "panel/staff_plan.html", context)
