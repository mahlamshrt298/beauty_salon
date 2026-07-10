from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User, Group
from urllib3 import request
from booking.models import Appointment,Staff
from services_app.models import ( Service ,PopularService, ServiceImage, Category as ServiceCategory, Subcategory,)
from django.db.models import Q , Count
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_POST
from core.models import SalonSettings
from accounts.models import Profile, Notification, DiscountCode
from datetime import datetime, timedelta , date , time
import jdatetime
from django.http import JsonResponse
from services_app.models import number_to_persian_words
import pytz
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
from django.core.cache import cache
from django.db.models import Case, When, IntegerField
from django.db.models import Sum, Q, Count, F
from django.utils import timezone
from booking.models import Payment, PackagePayment , Staff
from datetime import datetime , timedelta
from django.db.models import Count
from django.shortcuts import get_object_or_404
from booking.models import Staff, Appointment
from django.utils import timezone


#برای محدود کردن دسترسی به پنل
# مطمئن بشیم طرف هم لاگین کرده و هم حتما ادمین یا منشی هست.
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

    # خوندن مقادیر فیلتر از url
    year = request.GET.get("year")
    month = request.GET.get("month")

    appointments = Appointment.objects.all()

    #  فیلتر بر اساس سال و ماه (جداگانه یا ترکیبی)
    if year or month:
        if year and month:
            # هر دو انتخاب شده‌اند ،، فیلتر دقیق ماه
            jy = int(year)
            jm = int(month)
            start_j = jdatetime.date(jy, jm, 1)
            
            #هندل کردن ماه اسفند
            if jm == 12:
                end_j = jdatetime.date(jy + 1, 1, 1)
            else:
                end_j = jdatetime.date(jy, jm + 1, 1)
            
            #تبدیل شمسی به میلادی
            start_g = start_j.togregorian()
            end_g = end_j.togregorian()
            
            appointments = appointments.filter(
                appointment_date__gte=start_g,
                appointment_date__lt=end_g
            )
        
        elif year:
            # فقط سال انتخاب شده ،، کل سال
            jy = int(year)
            start_j = jdatetime.date(jy, 1, 1)
            end_j = jdatetime.date(jy + 1, 1, 1)
            
            start_g = start_j.togregorian()
            end_g = end_j.togregorian()
            
            appointments = appointments.filter(
                appointment_date__gte=start_g,
                appointment_date__lt=end_g
            )

    total_appointments = appointments.count()
    
    #آمار کلی
    #دیتای ثابت کش میشه، به مدت 5دقیقه
    total_services = cache.get('total_services')
    if total_services is None:
        total_services = Service.objects.count()
        cache.set('total_services', total_services, 300)

    total_staff = cache.get('total_staff')
    if total_staff is None:
        total_staff = User.objects.filter(groups__name="receptionist").count()
        cache.set('total_staff', total_staff, 300)
        
    # آمار وضعیت‌ها
    pending_bookings = appointments.filter(status="pending").count()
    confirmed = appointments.filter(status="confirmed").count()
    pending = appointments.filter(status="pending").count()
    cancelled = appointments.filter(status="cancelled").count()
    completed = appointments.filter(status="completed").count()

    #برای دراپ دوون
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
        "JALALI_MONTHS": JALALI_MONTHS,

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
   
   #  سرچ متنی
    q = request.GET.get("q")
    if q:
        appointments = appointments.filter(
            Q(user__username__icontains=q) |
            Q(service__name__icontains=q) |
            Q(status__icontains=q)|
            Q(staff__full_name__icontains=q)
        )

    #  فیلتر وضعیت ( دراپ دوون)
    status = request.GET.get("status")
    if status:
        appointments = appointments.filter(status=status)

    tracking = request.GET.get("tracking", "").strip()
    if tracking:
        appointments = appointments.filter(tracking_code__iexact=tracking)

    #  فیلتر بازه زمانی
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    if start_date and end_date:
        try:
            # تبدیل شمسی به میلادی برای فیلتر
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
                
                #تبدیل شمسی به میلادی
                start_gregorian_date = start_jalali_date.togregorian()
                end_gregorian_date = end_jalali_date.togregorian()
                
                appointments = appointments.filter(
                    appointment_date__gte=start_gregorian_date,
                    appointment_date__lte=end_gregorian_date
                )
        except (ValueError, IndexError, jdatetime.datetime.DateError):
            # اگر خطا داد، فیلتر تاریخ رو نادیده بگیر
            pass 

    converted_appointments = []
    month_names = {  
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
        #  تبدیل میلادی به شمسی برای نمایش
        j_date = jdatetime.date.fromgregorian(date=item.appointment_date)

        item.shamsi_date = f"{j_date.day} {month_names[j_date.month]} {j_date.year}"
        
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
        
        #  پیدا کردن شماره‌های تماس برای هر نوبت
        profile_phone = None
        if hasattr(item.user, 'profile') and item.user.profile.phone:
            profile_phone = item.user.profile.phone
        
        appt_phone = item.phone
        
        #  اگر هر دو وجود دارند و متفاوت هستند
        if profile_phone and appt_phone and profile_phone != appt_phone:
            item.display_phones = [
                {'number': profile_phone, 'label': 'پروفایل'},
                {'number': appt_phone, 'label': 'رزرو'}
            ]

         #  اگر فقط یکی وجود دارد
        elif profile_phone:
            item.display_phones = [{'number': profile_phone, 'label': 'پروفایل'}]
        elif appt_phone:
            item.display_phones = [{'number': appt_phone, 'label': 'رزرو'}]
        else:
            item.display_phones = None
            
        converted_appointments.append(item)
        
    paginator = Paginator(converted_appointments, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "panel/booking_list.html",
        {"appointments": page_obj,  "q": q, "status": status,"start_date": start_date, 
        "end_date": end_date,
        "tracking": tracking,  },
    )

#تایید نوبت
@require_POST
@login_required
@panel_access_required
def booking_approve(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    appointment.status = "confirmed"
    appointment.save()

    messages.success(request, "نوبت تأیید شد.", extra_tags = "panel")
    #برگرده همونجایی که بوده
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or reverse('panel:booking_list')
    return redirect(next_url)

#لغو نوبت
@require_POST
@login_required
@panel_access_required
def booking_cancel(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    appointment.status = "cancelled"
    appointment.save()

    messages.error(request, "نوبت لغو شد.", extra_tags = "panel")
    next_url = request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect("panel:booking_list")

@login_required
@panel_access_required
def booking_update(request, booking_id):
    appointment = get_object_or_404(Appointment, id=booking_id)
    if appointment.status not in ["pending", "confirmed"]:
        messages.warning(request, "این نوبت قابل ویرایش نیست.", extra_tags="panel")
        return redirect("panel:booking_list")
  
    if appointment.status == "confirmed" and request.user.profile.role not in ["owner", "receptionist"]:
        messages.warning(
            request,
            "نوبت تأیید شده است و فقط مدیر می‌تواند آن را ویرایش کند." , extra_tags = "panel"
        )
        return redirect("panel:booking_list")

    if request.user.profile.role not in ["owner", "receptionist"]:
        messages.error(request, "شما اجازه ویرایش ندارید" , extra_tags = "front")
        return redirect("panel:booking_list")
    
    services = Service.objects.all()
    staff_members = Staff.objects.all()

    jalali_date = jdatetime.date.fromgregorian(date=appointment.appointment_date)
    jalali_date_str = f"{jalali_date.year}/{jalali_date.month:02d}/{jalali_date.day:02d}"
    today_jalali = jdatetime.date.today()
    yesterday_jalali = today_jalali - jdatetime.timedelta(days=1)

    context = {
        "appointment": appointment,
        "services": services,
        "staff": staff_members,
        "jalali_date_str": jalali_date_str,
        "jalali_year": jalali_date.year,
        "jalali_month": jalali_date.month,
        "jalali_day": jalali_date.day,
        "jalali_today_str": f"{today_jalali.year}{today_jalali.month:02d}{today_jalali.day:02d}",
        "jalali_today_formatted": f"{today_jalali.year}/{today_jalali.month:02d}/{today_jalali.day:02d}",
        "jalali_yesterday_formatted": f"{yesterday_jalali.year}/{yesterday_jalali.month:02d}/{yesterday_jalali.day:02d}",
        "jalali_yesterday_str": f"{yesterday_jalali.year}{yesterday_jalali.month:02d}{yesterday_jalali.day:02d}",
    }

    if request.method == "POST":
        new_date_str = request.POST.get("date") 
        new_time_str = request.POST.get("start_time")
        service_id = request.POST.get("service")
        staff_id = request.POST.get("staff")

        if not new_time_str:
            messages.error(request, "ساعت نوبت ارسال نشده است", extra_tags="panel")
            return render(request, "panel/booking_update.html", context)

        #  اعتبار سنجی و تبدیل شمسی به میلادی
        try:
            jy, jm, jd = map(int, new_date_str.split("/"))
            new_date_gregorian = jdatetime.date(jy, jm, jd).togregorian()

            selected_jalali = jdatetime.date(jy, jm, jd)
                
            if selected_jalali < today_jalali:
                messages.error(
                        request, 
                        "تاریخ نمی‌تواند دیروز یا قبل‌تر باشد. لطفاً تاریخ امروز یا آینده را انتخاب کنید.",
                        extra_tags="panel"
                )
                return render(request, "panel/booking_update.html", context)

        except (ValueError, AttributeError):
            messages.error(request, "فرمت تاریخ نامعتبر است. لطفاً از فرمت 1404/12/16 استفاده کنید.", extra_tags="panel")
            return render(request, "panel/booking_update.html", context)
        
        if not service_id or not staff_id:
            messages.error(request, "سرویس و پرسنل را انتخاب کنید.", extra_tags="panel")
            return render(request, "panel/booking_update.html", context)

        service = get_object_or_404(Service, id=service_id)
        staff = get_object_or_404(Staff, id=staff_id)

        start_time = datetime.strptime(new_time_str, "%H:%M").time()

        #  محاسبه end_time
        dt = datetime.combine(new_date_gregorian, start_time)  
        end_dt = dt + timedelta(minutes=service.duration_minutes)
        end_time = end_dt.time()

        # بررسی روز کاری پرسنل 
        days_map = {0: 'شنبه', 1: 'یکشنبه', 2: 'دوشنبه', 3: 'سه‌شنبه', 4: 'چهارشنبه', 5: 'پنج‌شنبه', 6: 'جمعه'}
        
        selected_day_name = days_map[selected_jalali.weekday()]
        
        if selected_day_name not in staff.work_days:
            messages.error(request, f"پرسنل انتخابی در روز {selected_day_name} حضور ندارد.", extra_tags="panel")
            return render(request, "panel/booking_update.html", context)

        #ساعت نوبت تو بازه شیفت کاریش هست؟ 
        if start_time < staff.work_start_time or end_time > staff.work_end_time:
            messages.error(
                request, 
                f"ساعت انتخابی خارج از شیفت پرسنل است. (شیفت کاری: {staff.work_start_time.strftime('%H:%M')} تا {staff.work_end_time.strftime('%H:%M')})", 
                extra_tags="panel"
            )
            return render(request, "panel/booking_update.html", context)
        
        # تداخل با ساعت ناهار نداشته باشه
        if staff.has_lunch_break:
            if start_time < staff.lunch_end and end_time > staff.lunch_start:
                messages.error(
                    request, 
                    f"این ساعت با زمان استراحت/ناهار پرسنل تداخل دارد. (ناهار: {staff.lunch_start.strftime('%H:%M')} تا {staff.lunch_end.strftime('%H:%M')})", 
                    extra_tags="panel"
                )
                return render(request, "panel/booking_update.html", context)
            
        #  بررسی تداخل (با نوبت کس دیگه‌ای تو همون تایم تداخل نداشته باشه)
        #برای زمان:شروع ما قبل از پایان اونا باشه و پایان ما بعد از شروع اونا
        conflict = Appointment.objects.filter(
            staff_id=staff.id,
            appointment_date=new_date_gregorian,
            status__in=['pending', 'confirmed'],
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(id=appointment.id).exists()

        if conflict:
            messages.error(
                    request,
                    "در این تاریخ و ساعت قبلاً نوبت ثبت شده است.",
                    extra_tags="panel"
                )
            return render(request, "panel/booking_update.html", context)
        
        # اگر همه چی اوکی بود،  ذخیره میکنیم
        # دریافت وضعیت انتخاب شده از فرم
        new_status = request.POST.get("status")

        appointment.appointment_date = new_date_gregorian  
        appointment.start_time = start_time
        appointment.end_time = end_time
        appointment.service = service
        appointment.notes = request.POST.get("notes", "")
        appointment.staff_id = staff_id

        if new_status:
            appointment.status = new_status

        appointment.save()

        messages.success(request, "نوبت با موفقیت ویرایش شد.", extra_tags="panel")
        return redirect("panel:booking_list")

    return render(request, "panel/booking_update.html", context)



@login_required
@panel_access_required
def get_staff_by_service(request):
    service_id = request.GET.get('service_id')
    if service_id:
        staff_members = Staff.objects.filter(services__id=service_id, is_active=True, status="active")
        data = [{"id": s.id, "name": s.full_name} for s in staff_members]
        return JsonResponse({"staff": data})
    return JsonResponse({"staff": []})



#ثبت وضعیت انجام شده
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

#ثبت وضعیت عدم حضور
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
    #اول تاییدشده‌ها بیان بالا،بعد در انتظار تایید ها
    appointments = Appointment.objects.filter(
        appointment_date=today,
        status__in=['pending', 'confirmed']
    ).order_by(
        Case(
            When(status='confirmed', then=0),
            When(status='pending', then=1),
            output_field=IntegerField()
        ),
        'start_time'
    )
    
    #   شماره‌های تماس برای هر نوبت
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

    paginator = Paginator(appointments_list, 10) 
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
        status__in=['pending', 'confirmed']  
    ).select_related('user', 'service', 'staff', 'user__profile').order_by('start_time')
    
    # اول نوبت‌های در انتظار، بعد تأیید شده، سپس بر اساس ساعت
    appointments = appointments.order_by(
        '-status',  
        'start_time'
    )

    #   شماره‌های تماس برای هر نوبت 
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

#در اضافه یا ویرایش خدمت استفاده شده
@login_required
@panel_access_required
def load_subcategories(request):
    category_id = request.GET.get('category_id')
    subcategories = Subcategory.objects.filter(category_id=category_id).values('id', 'name')
    return JsonResponse(list(subcategories), safe=False)

@login_required
@panel_access_required
def services_list(request):

    # خوندن پارامترهای فیلتر از URL
    category_id = request.GET.get("category")
    subcategory_id = request.GET.get("subcategory")
    status_filter = request.GET.get("status")
    
    #واسه باز کردن مودال ویرایش و حذف دسته‌بندی‌
    danger_category_id = request.GET.get("danger_category")
    if danger_category_id in ["", "None", None]:
        danger_category_id = None

    services = Service.objects.all().order_by('-id')
    
    #اعمال فیلترها
    if category_id:
        services = services.filter(subcategory__category_id=category_id)

    if subcategory_id:
        services = services.filter(subcategory_id=subcategory_id)

    if status_filter == "active":
        services = services.filter(is_active=True)
    elif status_filter == "inactive":
        services = services.filter(is_active=False)

    paginator = Paginator(services, 15)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    #گرفتن لیست دسته‌ها همراه با تعداد زیردسته‌هاشون
    categories = ServiceCategory.objects.annotate(
        sub_count=Count("subcategories")
    )

    #  واسه دراپ‌داون فیلتر زیردسته‌ها
    if category_id:
        subcategories = Subcategory.objects.filter(category_id=category_id)
    else:
        subcategories = Subcategory.objects.none()

    #  برای کارت مدیریت زیردسته‌ها
    if danger_category_id and danger_category_id.isdigit():
        danger_subcategories = Subcategory.objects.filter(category_id=danger_category_id).annotate(service_count=Count("services"))
    else:
        danger_subcategories = Subcategory.objects.none()


    return render(request, "panel/services_list.html", {"services": page_obj,
            "categories": categories,
            "subcategories": subcategories,
            "selected_category": category_id,
            "selected_subcategory": subcategory_id,
            "selected_status": status_filter,
            "danger_subcategories": danger_subcategories,
            "selected_danger_category": danger_category_id,
            })

@login_required
@panel_access_required
def service_add(request):
    #آماده‌سازی فرم‌ست واسه آپلود چندتایی عکس
    #گالری سرویس
    GalleryFormSet = modelformset_factory(ServiceImage, form=ServiceGalleryForm, extra=1, can_delete=True)

    if request.method == "POST":
        # چون عکس داریم، حتما باید request.FILES رو پاس بدیم
        form = ServiceForm(request.POST, request.FILES)

        if form.is_valid() :
            service = form.save()

            #  لوپ میزنیم روی عکس‌هایی که کاربر آپلود کرده 
            # و اون‌ها رو به گالری همین سرویس متصل میکنیم
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

            # اضافه کردن عکس‌های جدید به گالری
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
    
    #برمیگردونیم به همون صفحه‌ای که توش بوده
    next_url = request.META.get("HTTP_REFERER")
    if next_url:
        return redirect(next_url)

    return redirect("panel:service_edit", id=service_id)


# مدیریت دسته‌ها و زیردسته‌ها
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

@login_required
@panel_access_required
def category_edit(request, id):
    category = get_object_or_404(ServiceCategory, id=id)

    if request.method == "POST":
        name = request.POST.get("name")

        if name:
            category.name = name
            category.slug = ""  
            category.save()
            messages.success(request, "دسته با موفقیت ویرایش شد.", extra_tags="panel")

            #اگه از مودالِ بخش دسته‌ها اومده، دوباره برش گردونیم همونجا
            danger_category = request.POST.get("danger_category")

            if danger_category and danger_category.isdigit():
                return redirect(
                    f"{reverse('panel:services_list')}?danger_category={danger_category}"
                )

            return redirect("panel:services_list")

    return render(request, "panel/category_edit.html", {
        "category": category
    })

@login_required
@panel_access_required
def subcategory_edit(request, id):
    subcategory = get_object_or_404(Subcategory, id=id)
    categories = ServiceCategory.objects.all()

    if request.method == "POST":
        name = request.POST.get("name")
        category_id = request.POST.get("category")

        if name and category_id:
            subcategory.name = name
            subcategory.category_id = category_id
            subcategory.slug = ""
            subcategory.save()
            messages.success(request, "زیردسته با موفقیت ویرایش شد.", extra_tags="panel")
            
            danger_category = request.POST.get("danger_category")

            if danger_category and danger_category.isdigit():
                return redirect(
                    f"{reverse('panel:services_list')}?danger_category={danger_category}"
                )

            return redirect("panel:services_list")

    return render(request, "panel/subcategory_edit.html", {
        "subcategory": subcategory,
        "categories": categories
    })


@require_POST
@login_required
@panel_access_required
def service_delete_category(request, id):
    category = get_object_or_404(ServiceCategory, id=id)
    #نباید دسته‌ای رو که زیردسته یا سرویس داره پاک کنیم
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
    #اگر زیر دسته خودش سرویس داشت،جلوی حذفش رو میگیریم
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

    #فقط مدیر میتونه اینکار رو انجام بده
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

    #  واکشی مدیر و منشی‌ها از مدل Profile
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

    # واکشی پرسنل سالن 
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


    paginator = Paginator(personnel, 12)  
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
        # اول مطمئن میشیم فیلدهای ضروری حتما پر شده باشن
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
            # اعتبارسنجی شماره موبایل 
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
        user.profile.role = "receptionist"
        user.profile.save()

        # تعیین گروه
        group = Group.objects.get(name="receptionist")
        user.groups.add(group)

        # فعال‌سازی دسترسی به پنل مدیریت
        user.is_staff = True
        user.save()

        messages.success(request, "منشی با موفقیت اضافه شد." , extra_tags = "panel")
        return redirect("panel:staff_list")  

    return render(request, "panel/staff_add.html")

@login_required
@panel_access_required
def staff_edit(request, id):
    staff = get_object_or_404(User, id=id)

    if not staff.is_active:
        messages.warning(request, "این پرسنل غیرفعال است و قابل ویرایش نیست" , extra_tags = "panel")
        return redirect("panel:staff_list")


    if request.method == "POST":
        required_fields = ["username","first_name","last_name","phone"]
        for f in required_fields:
            if not request.POST.get(f):
                messages.error(request, f"فیلد {f} نمی‌تواند خالی باشد.", extra_tags="panel")
                return redirect("panel:staff_add")
            
        username = request.POST.get("username")
        password = request.POST.get("password", "").strip()
        confirm_password = request.POST.get("confirm_password", "").strip()

        #چک کردن تغییر پسورد
        if password:
            if password != confirm_password:
                messages.error(request, "رمز عبور و تکرار آن یکسان نیست.", extra_tags="panel")
                return redirect("panel:staff_edit", id=id)
            staff.set_password(password)

        # بررسی نام کاربری تکراری
        if User.objects.filter(username=username).exclude(id=staff.id).exists():
            messages.error(request, "این نام کاربری قبلاً ثبت شده است." , extra_tags = "panel")
            return redirect("panel:staff_edit", id=staff.id)

        staff.username = username

        if password and password.strip() != "":
            staff.set_password(password)

        staff.save()

        # آپدیت کردن پروفایل
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
    
    profile.status = status
    profile.save()   

    if status == "inactive":
        profile.user.is_active = False
    else:
        profile.user.is_active = True

    profile.user.save()

    #  ساخت اعلان
    status_labels = {
        "active": "فعال",
        "inactive": "غیرفعال",
        "leave": "مرخصی",
    }

    Notification.objects.create(
        user=profile.user,
        type="status_change",
        channel="email", 
        message=f"وضعیت شما توسط مدیر به «{status_labels[status]}» تغییر یافت."
    )

    #ارسال ایمیل
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
        full_name = request.POST.get("full_name", "").strip()
        role = request.POST.get("role", "").strip()
        phone = request.POST.get("phone", "").strip()
        work_start_time = request.POST.get("work_start_time")
        work_end_time = request.POST.get("work_end_time")
        photo = request.FILES.get("photo")
        show_in_about_page = request.POST.get("show_in_about_page") == "on"
        
        #  اعتبارسنجی شماره تماس
        if not phone:
            messages.error(request, "شماره تماس الزامی است.", extra_tags="panel")
            return redirect("panel:salon_staff_add")
        
        if not re.match(r"^09\d{9}$", phone):
            messages.error(
                request,
                "شماره تماس باید ۱۱ رقم باشد و با 09 شروع شود",
                extra_tags="panel"
            )
            return redirect("panel:salon_staff_add")
        
        #  اعتبارسنجی روزهای کاری
        work_days = request.POST.getlist("work_days")
        if not work_days:
            messages.error(
                request,
                "لطفاً حداقل یک روز کاری انتخاب کنید.",
                extra_tags="panel"
            )
            return redirect("panel:salon_staff_add")

        #  اعتبارسنجی خدمات
        service_ids = request.POST.getlist("services")

        if not service_ids:
            messages.error(
                request,
                "لطفاً حداقل یک خدمت انتخاب کنید.",
                extra_tags="panel"
            )
            return redirect("panel:salon_staff_add")

        # ثبت خود شخص
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

        valid_ids = [int(sid) for sid in service_ids if sid.isdigit()]
        services_qs = Service.objects.filter(id__in=valid_ids)
        staff.services.set(services_qs)
        
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
        staff.is_active = True  

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

        #  روزهای کاری 
        staff.work_days = request.POST.getlist("work_days")

        #  ساعت کاری
        staff.work_start_time = request.POST.get("work_start_time")
        staff.work_end_time = request.POST.get("work_end_time")

        #  وضعیت
        staff.status = request.POST.get("status")

        #  فعال / غیرفعال
        staff.is_active = "is_active" in request.POST

        # اگر عکس جدید آپلود شده باشد، جایگزین می‌شود
        if request.FILES.get("photo"):
            staff.photo = request.FILES.get("photo")
        
        staff.show_in_about_page = request.POST.get("show_in_about_page") == "on"

        staff.save()

         #  خدمات جدید 
        services_str = request.POST.get("services", "")
        service_ids = services_str.split(",") if services_str else []
        
        #  ذخیره خدمات
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


#برای کسایی که خواستن وارد مسیری بشن که دسترسی بهش رو ندارن
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
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category')
        order = request.POST.get('order', '').strip()
        image = request.FILES.get('image')

        #اعتبار سنجی فرم
        if not title or not description or not category_id or not image or order == '':
            messages.error(request, 'لطفاً همه فیلدهای اجباری را پر کنید.')
            return render(request, 'panel/popular_service_form.html', {
                'categories': categories
            })
        
        category = get_object_or_404(ServiceCategory, id=category_id)

        PopularService.objects.create(
            title=title,
            description=description,
            image=image,
            category=category,
            order=order,
            # چک باکس‌ها تو ریکوئست POST فقط در صورتی میان که تیک خورده باشن
            is_active='is_active' in request.POST
        )
        messages.success(request, 'خدمت پرطرفدار با موفقیت اضافه شد.')
        return redirect('panel:popular_services_list')

    return render(request, 'panel/popular_service_form.html',{'categories': categories})

@login_required
@panel_access_required
def popular_service_edit(request, pk):
    service = get_object_or_404(PopularService, pk=pk)
    categories = ServiceCategory.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category')
        order = request.POST.get('order', '').strip()

        if not title or not description or not category_id or order == '':
            messages.error(request, 'لطفاً همه فیلدهای اجباری را پر کنید.')
            return render(request, 'panel/popular_service_form.html', {
                'service': service,
                'categories': categories
            })
        
        service.title = title
        service.description = description
        service.category = get_object_or_404(ServiceCategory, id=category_id)
        service.order = order
        service.is_active = 'is_active' in request.POST

        # فقط اگه عکس جدید آپلود شده بود، فیلد عکس رو آپدیت کن
        if 'image' in request.FILES:
            service.image = request.FILES['image']

        service.save()
        messages.success(request, 'خدمت پرطرفدار با موفقیت ویرایش شد.')
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
    
    paginator = Paginator(articles, 12) 
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

    context = {
        'categories': categories,
        'services': services,
        'service_categories': service_categories,
        'subcategories': subcategories,
        'article': None,
    }

    if request.method == "POST":
        title   = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category', '').strip()

        #برای اینکه تو فرانت بتونیم زیر هر فیلد ارور خودش رو نشون بدیم
        errors = {}
        if not title:
            errors['title'] = "عنوان مقاله الزامی است."
        if not content:
            errors['content'] = "محتوای مقاله الزامی است."
        if not category:
            errors['category'] = "دسته‌بندی الزامی است."
        if not request.FILES.get('image'):
            errors['image'] = "تصویر مقاله الزامی است."

        # اگه اروری داشتیم، دوباره همون فرم رو رندر کن ولی دیتای قبلی رو هم بفرست
        if errors:
            messages.error(request, "لطفاً خطاهای زیر را برطرف کنید.", extra_tags="panel")
            context['errors'] = errors
            context['old'] = request.POST  
            return render(request, 'panel/article_form.html', context)
        
        Article.objects.create(
            title=title,
            content=content,
            image=request.FILES.get('image'),
            category_id=category,
            author=request.user,
            tags=request.POST.get('tags', ''),
            Key_points=request.POST.get('Key_points', ''),
            for_reserve_id=request.POST.get('for_reserve') or None,
            show_on_home = bool(request.POST.get("show_on_home"))
        )
        messages.success(request, "مقاله با موفقیت اضافه شد", extra_tags="panel")
        return redirect('panel:article_list')

    return render(request, 'panel/article_form.html', context)

@login_required
@panel_access_required
def article_edit(request, pk):
    article = get_object_or_404(Article, pk=pk)
    categories = BlogCategory.objects.all()
    service_categories = ServiceCategory.objects.all()
    subcategories = Subcategory.objects.all()
    services = Service.objects.filter(is_active=True)

    context = {
        'article': article,
        'categories': categories,
        'services': services,
        'service_categories': service_categories,
        'subcategories': subcategories,
    }

    if request.method == "POST":
        title   = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category', '').strip()

        errors = {}
        if not title:
            errors['title'] = "عنوان مقاله الزامی است."
        if not content:
            errors['content'] = "محتوای مقاله الزامی است."
        if not category:
            errors['category'] = "دسته‌بندی الزامی است."
        # اگه عکس جدید آپلود نشده و عکس قبلی هم نداریم ارور بده
        if not request.FILES.get('image') and not article.image:
            errors['image'] = "تصویر مقاله الزامی است."

        if errors:
            messages.error(request, "لطفاً خطاهای زیر را برطرف کنید.", extra_tags="panel")
            context['errors'] = errors
            return render(request, 'panel/article_form.html', context)
        
        article.title = title
        article.content = content
        article.category_id = category
        article.tags = request.POST.get('tags', '')
        article.Key_points = request.POST.get('Key_points', '')
        article.for_reserve_id = request.POST.get('for_reserve') or None
        article.show_on_home = bool(request.POST.get("show_on_home"))

        if 'image' in request.FILES:
            article.image = request.FILES['image']

        article.save()
        messages.success(request, "مقاله ویرایش شد", extra_tags="panel")
        return redirect('panel:article_list')

    return render(request, 'panel/article_form.html', context)

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
        name = request.POST.get('name', '').strip()
        
        if not name:
            messages.error(request, "نام دسته‌بندی الزامی است", extra_tags="panel")
            return render(request, 'panel/article_category_form.html')
        
        #دسته با این اسم تکراری نباشه
        if BlogCategory.objects.filter(name=name).exists():
            messages.error(request, "این دسته‌بندی قبلاً ثبت شده است", extra_tags="panel")
            return render(request, 'panel/article_category_form.html', {'name': name})
        
        BlogCategory.objects.create(name=name)
        messages.success(request, "دسته‌بندی اضافه شد", extra_tags="panel")
        return redirect('panel:article_category_list')

    return render(request, 'panel/article_category_form.html')

@login_required
@panel_access_required
def article_category_edit(request, pk):
    category = get_object_or_404(BlogCategory, pk=pk)

    if request.method == "POST":
        name = request.POST.get('name', '').strip()
        
        if not name:
            messages.error(request, "نام دسته‌بندی الزامی است", extra_tags="panel")
            return render(request, 'panel/article_category_form.html', {'category': category})
        
        #  خودش رو از چک تکراری حذف می‌کنه
        #وگرنه اگه کاربر روی دکمه سیو بزنه بدون اینکه اسم رو عوض کنه، بهش ارور میده
        if BlogCategory.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, "این دسته‌بندی قبلاً ثبت شده است", extra_tags="panel")
            return render(request, 'panel/article_category_form.html', {'category': category})
        
        category.name = name
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
    
    #فیلتر کردن نظرات
    if status == 'approved':
        reviews = reviews.filter(status = 'approved')

    elif status == 'rejected':
        reviews = reviews.filter(status = 'rejected')

    elif status == 'pending':
        reviews = reviews.filter(status = 'pending')
        
    paginator = Paginator(reviews, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    #  تبدیل تاریخ ایجاد نظر به شمسی 
    for review in page_obj:
        # تبدیل به زمان محلی پروژه (برای جلوگیری از اختلاف تاریخ)
        local_time = timezone.localtime(review.created_at)
        jalali_dt = jdatetime.datetime.fromgregorian(datetime=local_time)
        review.jalali_date_str = jalali_dt.strftime('%Y/%m/%d')
        review.jalali_time_str = jalali_dt.strftime('%H:%M') 

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
    
    # اگه از قبل تایید شده بود، الکی پردازش نکن
    if review.status == 'approved':
        messages.info(request, 'این نظر قبلاً تأیید شده است.', extra_tags='panel')
        return redirect('panel:review_list')
    
    review.status = 'approved'
    review.save(update_fields=['status'])
    messages.success(request, 'نظر تأیید شد', extra_tags='panel')
    
    #  ارسال ایمیل به کاربر
    email_sent = False
    if review.user and review.user.email:
        try:
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
                fail_silently=True,
            )
            email_sent = True
            logger.info(f"ایمیل تأیید نظر به {review.user.email} برای نظر #{review.id} ارسال شد")
        except Exception as e:
            logger.error(f"خطا در ارسال ایمیل تأیید نظر به {review.user.email}: {str(e)}")
    
    return redirect('panel:review_list')

@require_POST
@login_required
@panel_access_required
def review_reject(request, pk):
    review = get_object_or_404(Review, pk=pk)
    old_status = review.status
    
     #  اگر قبلاً رد شده
    if review.status == 'rejected':
        messages.info(request, 'این نظر قبلاً رد شده است.', extra_tags='panel')
        return redirect('panel:review_list')
    
    review.status = 'rejected'
    
    review.save(update_fields=['status'])
    messages.warning(request, 'نظر رد شد', extra_tags='panel')
    
     # ارسال ایمیل به کاربر
    email_sent = False
    if review.user and review.user.email:
        try:
            service_name = review.service.name if review.service else "خدمات سالن"
            
            #  اضافه کردن دلیل به متن ایمیل
            reason_text = f"\nدلیل رد نظر: {review.admin_reply}\n" if review.admin_reply else ""
            
            subject = 'نظر شما بررسی شد ❌'
            message = f"""سلام {review.user.get_full_name() or review.user.username} عزیز،

            با تشکر از نظر ارزشمند شما برای خدمت «{service_name}»، 
            متأسفانه نظر شما مطابق با سیاست‌های سایت نبود و پس از بررسی، قابل نمایش نیست.
            {reason_text}
            هرگونه پیشنهاد یا انتقاد دیگری دارید، خوشحال می‌شویم در پنل کاربری یا از طریق تماس با ما با ما در میان بگذارید.

            با احترام،
            تیم سالن زیبایی نورا
            """

            send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [review.user.email],
                    fail_silently=True,
                )
            email_sent = True
        except Exception as e:
            logger.error(f"خطا در ارسال ایمیل رد نظر به {review.user.email}: {str(e)}")
  
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

#واسه شمسی کردن تاریخ انقضا
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
        #حذف کد تخفیف
        if "delete_id" in request.POST:
            DiscountCode.objects.filter(id=request.POST["delete_id"]).delete()
            return redirect("panel:discount_codes")

        #فعال/غیرفعال کردن
        # اگه دکمه تغییر وضعیت زده شده بود
        if "toggle_active" in request.POST:
            code_id = request.POST["toggle_active"]
            code = DiscountCode.objects.get(id=code_id)
            code.is_active = not code.is_active
            code.save()

            # وقتی فعال شد اعلان بفرست
            if code.is_active and not code.notification_sent:
                code.notification_sent = True
                code.notification_sent_at = timezone.now()
                code.save()

                target_users = User.objects.filter(is_active=True)

                #  اعلان‌های قبلی این کد تخفیف حذف شود
                Notification.objects.filter(discount=code).delete()

                # ساخت نوتیفیکیشن برای همه کاربرا
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
                            subject, body, None, [user.email], fail_silently=True
                        )
                        Notification.objects.filter(
                            user=user, discount=code
                        ).update(status="sent", sent_at=timezone.now())
                    except Exception as e:
                        logger.warning(f"ارسال ایمیل به {user.email} شکست: {e}")

                return redirect("panel:discount_codes")
        
        # ارسال دوباره اعلان
        if "resend_notify" in request.POST:
            code = DiscountCode.objects.get(id=request.POST["resend_notify"])
            code.notification_sent = True
            code.notification_sent_at = timezone.now()
            code.save()
            
            #نوتیف‌های قبلی رو پاک میکنه و از نو میسازه و ایمیل می‌فرسته
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
                        extra=code.extra_message,
                    )
                try:
                    send_mail(
                            subject, body, None, [user.email], fail_silently=True
                        )
                    Notification.objects.filter(
                            user=user, discount=code
                        ).update(status="sent", sent_at=timezone.now())
                except Exception as e:
                    logger.warning(f"ارسال ایمیل به {user.email} شکست: {e}")

            return redirect("panel:discount_codes")
        
    # جستجو
    query = request.GET.get("search", "")
    
    status = request.GET.get("status", "") 

    codes = DiscountCode.objects.all().order_by('-id')

    if query:
        codes = codes.filter(code__icontains=query)

    if status == "active":
        codes = codes.filter(is_active=True)
    elif status == "inactive":
        codes = codes.filter(is_active=False)
        
    paginator = Paginator(codes, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "panel/discount_codes.html", {
        "codes": page_obj,
        "query": query,
        "status": status,
    })


User = get_user_model()

@login_required
@panel_access_required
def discount_code_create(request):
    if request.method == "POST":
        form = DiscountCodeForm(request.POST)
        if form.is_valid():
            discount = form.save(commit=False)   # نهایی‌سازی نکن ،  تو دیتابیس سیو نشه
            discount.user = request.user 

            # اگر موقع ساختن تیک فعال رو زده باشه، همون لحظه ایمیل‌ها رو براش می‌فرستیم
            if discount.is_active:
                discount.notification_sent = True
                discount.notification_sent_at = timezone.now()
                discount.save()
            
                # کاربران هدف  
                target_users = User.objects.filter(is_active=True)

                # ایجاد اعلان‌ها
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
                            None,               
                            [user.email],
                            fail_silently=True,
                        )
                        Notification.objects.filter(user=user, discount_id=discount.id,).update(status="sent", sent_at=timezone.now())
                    except Exception as e:         
                        logger.warning(
                            f"ارسال ایمیل به {user.email} شکست: {e}"
                        )
                        continue
                messages.success(request, "کد تخفیف با موفقیت ثبت شد و اعلان برای کاربران ارسال شد.")
            else:
                # غیر فعال → فقط ذخیره می‌کنیم و ایمیل نمیفرستیم
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
            discount = form.save(commit=False) 
            discount.user = request.user  
              # اگر وضعیت فعال شد و قبلاً اعلان نرفته بود،حالا ایمیل میفرستیم
            if discount.is_active and not discount.notification_sent:
                discount.notification_sent = True
                code.notification_sent_at = timezone.now()

                discount.save()
                #  کاربران هدف  
                target_users = User.objects.filter(is_active=True)

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
                            None,                 
                            [user.email],
                            fail_silently=True,
                        )
                        Notification.objects.filter(
                            user=user,
                            discount_id=discount.id,
                        ).update(status="sent", sent_at=timezone.now())
                    
                    except Exception as exc:
                        logger.warning(
                            f"ارسال ایمیل به {user.email} شکست: {exc}"
                        )

                messages.success(request, "کد تخفیف با موفقیت ثبت شد و اعلان برای کاربران ارسال شد.")
            else:
                # غیرفعال یا قبلاً اعلان ارسال شده ،، فقط ذخیره
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
    
    #  گرفتن ماه و سال جاری شمسی
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
    
    paginator = Paginator(holidays, 10)  
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
        date_str = request.POST.get('date', '').strip()  
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '')
        holiday_type = request.POST.get('holiday_type', '').strip()
        # چک باکس‌ها تو ریکوئست POST اگه تیک خورده باشن مقدار 'on' میفرستن
        is_active = request.POST.get('is_active') == 'on'
        is_half_day = request.POST.get('is_half_day') == 'on'
        half_day_period = request.POST.get('half_day_period', '')
        
        #اعتبارسنجی
        errors = []
        if not date_str:
            errors.append("تاریخ شمسی الزامی است.")
        if not title:
            errors.append("عنوان تعطیلی الزامی است.")
        if not holiday_type or holiday_type not in ['official', 'religious', 'custom']:
            errors.append("نوع تعطیلی الزامی است.")

        if errors:
            for err in errors:
                messages.error(request, err, extra_tags="panel")
            return render(request, 'panel/holiday_form.html', {
                'post_data': request.POST       # برای نگه داشتن مقادیر قبلی
            })
        
        try:
            # تبدیل تاریخ شمسی به میلادی
            year, month, day = map(int, date_str.split('/'))
            jalali_date = jdatetime.date(year, month, day)
            gregorian_date = jalali_date.togregorian()
            
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
        date_str = request.POST.get('date', '').strip()
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '')
        holiday_type = request.POST.get('holiday_type', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        is_half_day = request.POST.get('is_half_day') == 'on'
        half_day_period = request.POST.get('half_day_period', '')
        
        errors = []
        if not date_str:
            errors.append("تاریخ شمسی الزامی است.")
        if not title:
            errors.append("عنوان تعطیلی الزامی است.")
        if not holiday_type or holiday_type not in ['official', 'religious', 'custom']:
            errors.append("نوع تعطیلی الزامی است.")

        if errors:
            for err in errors:
                messages.error(request, err, extra_tags="panel")
            return render(request, 'panel/holiday_form.html', {
                'holiday': holiday,
                'jalali_date_str': date_str,
                'post_data': request.POST  
            })
        
        try:
            # تبدیل تاریخ شمسی به میلادی
            year, month, day = map(int, date_str.split('/'))
            jalali_date = jdatetime.date(year, month, day)
            gregorian_date = jalali_date.togregorian()
            
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
    #برای تغییر وضعیت
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
    if request.user.profile.role not in ["owner", "receptionist"]:
        messages.error(request, "شما مجوز دسترسی ندارید" , extra_tags="panel")
        return redirect('panel:dashboard')
    
    settings, created = SalonSettings.objects.get_or_create(id=1)
    
    #  منشی حق ویرایش نداره، فقط میتونه ببینه
    is_read_only = (request.user.profile.role == "receptionist")

    weekdays = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']

    if request.method == 'POST':
        if request.user.profile.role != "owner":
            messages.error(request, "فقط مالک سالن می‌تواند تنظیمات را ویرایش کند", extra_tags="panel")
            return redirect('panel:salon_settings')

        salon_name = request.POST.get('salon_name', '').strip()
        if not salon_name:
            messages.error(request, "نام سالن الزامی است", extra_tags="panel")
            return redirect('panel:salon_settings')

        weekend_days = request.POST.getlist('weekend_days')
        if not weekend_days:
            messages.error(request, "حداقل یک روز تعطیل هفتگی باید انتخاب شود", extra_tags="panel")
            return redirect('panel:salon_settings')
        
        settings.salon_name = salon_name
        settings.open_time = request.POST.get('open_time', '09:00')
        settings.close_time = request.POST.get('close_time', '18:00')
        settings.has_salon_lunch_break = request.POST.get('has_salon_lunch_break') == 'on'
        settings.salon_lunch_start = request.POST.get('salon_lunch_start', '13:00')
        settings.salon_lunch_end = request.POST.get('salon_lunch_end','14:00')
        settings.enable_online_payment = request.POST.get('enable_online_payment') == 'on'
        settings.global_duration_note = request.POST.get('global_duration_note', '').strip()
        settings.global_price_note = request.POST.get('global_price_note', '').strip()

        settings.weekend_days = weekend_days

        phone = request.POST.get('phone', '').strip()

        pattern = r'^(09\d{9}|0\d{10})$'

        if not re.match(pattern, phone):
            messages.error(request, "شماره تماس معتبر نیست", extra_tags="panel")
            return redirect('panel:salon_settings')

        settings.phone = phone

        whatsapp = request.POST.get('whatsapp', '').strip()

        if whatsapp:
            whatsapp_pattern = r'^989\d{9}$'
            if not re.match(whatsapp_pattern, whatsapp):
                messages.error(request, "شماره واتساپ باید به صورت 989xxxxxxxxx باشد", extra_tags="panel")
                return redirect('panel:salon_settings')

        settings.whatsapp = whatsapp
        instagram = request.POST.get('instagram', '').strip()
        settings.instagram = instagram

        settings.save()
        messages.success(request, "تنظیمات ذخیره شد", extra_tags="panel")
        return redirect('panel:salon_settings')
    
    return render(request, 'panel/salon_settings.html', {'settings': settings , 'is_read_only': is_read_only,'weekdays': weekdays})


#پکیج ها-پیشنهاد های ویژه
# -----------------------------

# لیست پکیج‌ها
@login_required
@panel_access_required
def package_list(request):
    packages = Package.objects.all().prefetch_related('service').order_by('-created_at')
    
    paginator = Paginator(packages, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'panel/package_list.html', {
        'packages': page_obj
    })

# افزودن پکیج جدید
@login_required
@panel_access_required
def package_add(request):    
    categories = ServiceCategory.objects.all()

    if request.method == 'POST':
        package = Package()
        package.title = request.POST.get('title')
        package.description = request.POST.get('description')
        package.original_price = request.POST.get('original_price') or None
        package.discounted_price = request.POST.get('discounted_price')
        package.discount_badge = request.POST.get('discount_badge', '')
        package.is_active = 'is_active' in request.POST
        
        # مدیریت تخفیف موقت
        if 'is_limited_time' in request.POST:
            package.is_limited_time = True
            package.duration_days = int(request.POST.get('duration_days', 3))

            start_time_str = request.POST.get('start_time')

            if not start_time_str:
                messages.error(request, "لطفاً زمان شروع تخفیف را انتخاب کنید", extra_tags="panel")
                return render(request, 'panel/package_form.html', {
                    'package': package,
                    'categories': categories,
                    'action': 'add'
                })

            try:
                naive_start = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')

                tehran_tz = pytz.timezone('Asia/Tehran')
                start_time = tehran_tz.localize(naive_start)
                now = timezone.now().astimezone(tehran_tz)
                
                #زمان شروع تخفییف نمیتونه توی گذشته باشه
                if start_time <= now:
                    messages.error(request, "زمان شروع تخفیف باید در آینده باشد", extra_tags="panel")
                    return render(request, 'panel/package_form.html', {
                        'package': package,
                        'categories': categories,
                        'action': 'add'
                    })

                package.start_time = start_time

            except ValueError as e:
                print(f"ValueError: {e}, start_time_str: {start_time_str}")
                messages.error(request, "فرمت تاریخ نامعتبر است", extra_tags="panel")
                return render(request, 'panel/package_form.html', {
                    'package': package,
                    'categories': categories,
                    'action': 'add'
                })

        else:
            package.is_limited_time = False
            package.start_time = None
            
        # عکس
        if 'image' in request.FILES:
            package.image = request.FILES['image']
        
        # نمایش در سایت
        package.show_on_homepage = request.POST.get('show_on_homepage') == '1'

        package.save()
        
        service_ids = request.POST.getlist('services[]')
        if service_ids:
            services = Service.objects.filter(id__in=service_ids)
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
    categories = ServiceCategory.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "لطفاً عنوان پکیج را وارد کنید", extra_tags="panel")
            return render(request, 'panel/package_form.html', {
                'package': package,
                'categories': categories,
                'action': 'edit'
            })

        package.title = title
        package.description = request.POST.get('description')
        package.original_price = request.POST.get('original_price') or None
        package.discounted_price = request.POST.get('discounted_price')
        package.discount_badge = request.POST.get('discount_badge', '')
        package.is_active = 'is_active' in request.POST
        
        # مدیریت تخفیف موقت
        if 'is_limited_time' in request.POST:
            package.is_limited_time = True
            package.duration_days = int(request.POST.get('duration_days', 3))

            start_time_str = request.POST.get('start_time')

            if not start_time_str:
                messages.error(request, "لطفاً زمان شروع تخفیف را انتخاب کنید", extra_tags="panel")
                return render(request, 'panel/package_form.html', {
                    'package': package,      
                    'categories': categories,
                    'action': 'edit'         
                })

            try:
                naive_start = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
                
                tehran_tz = pytz.timezone('Asia/Tehran')
                #ساعت رو تو تایم‌زون تهران بومی‌سازی می‌کنه که اختلاف ساعت سرور باعث نشه تخفیف زودتر یا دیرتر فعال بشه.
                start_time = tehran_tz.localize(naive_start)
                
                now = timezone.now().astimezone(tehran_tz)
                

                if start_time <= now:
                    messages.add_message(request, messages.ERROR, "زمان شروع تخفیف باید در آینده باشد", extra_tags='panel')
                    return render(request, 'panel/package_form.html', {
                        'package': package,  
                        'categories': categories,
                        'action': 'edit'    
                    })

                package.start_time = start_time

            except ValueError as e:
                messages.error(request, "فرمت تاریخ نامعتبر است", extra_tags="panel")
                return render(request, 'panel/package_form.html', {
                    'package': package,
                    'categories': categories,
                    'action': 'edit'
                })

        else:
            package.is_limited_time = False
            package.start_time = None
                    
        # عکس جدید
        if 'image' in request.FILES:
            package.image = request.FILES['image']
        
        # نمایش در سایت
        package.show_on_homepage = request.POST.get('show_on_homepage') == '1'

        package.save()
        
        service_ids = request.POST.getlist('services[]')
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
    """ارسال ایمیل با پشتیبانی از هر دو روش"""
    
    users = User.objects.filter(is_active=True, email__isnull=False).exclude(email='')
    
    if not users.exists():
        return
    
    subject = f"🎁 پیشنهاد ویژه: {package.title}"
    
    message = f"""
    سلام 🌸
    
    یه خبر خوب برات داریم!
    
    پکیج جدید «{package.title}» به مجموعه ما اضافه شد.
    
    💰 قیمت: {package.discounted_price:,} تومان
    
    برای مشاهده و رزرو به سایت ما سر بزنید.
    
    با احترام
    تیم سالن زیبایی
    """
    
    success_count = 0
    for user in users:
        try:
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,  
            )
            success_count += 1
            print(f"✅ ایمیل به {user.email} ارسال شد")
        except Exception as e:
            print(f"❌ خطا در ارسال به {user.email}: {str(e)}")
            continue
    
    print(f"📊 نتیجه: {success_count} از {len(users)} ایمیل ارسال شد")
    

#برای ارسال دوباره ایمیل: دکمه اش توسط ادمین زده میشه
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

    # گرفتن فیلترها از URL
    payment_method = request.GET.get("method")
    status = request.GET.get("status")
    start_date_str = request.GET.get("start_date") 
    end_date_str = request.GET.get("end_date")

    #بررسی بازه تاریخ
    if start_date_str and end_date_str:
        try:
            jalali_start = jdatetime.datetime.strptime(start_date_str, "%Y/%m/%d")
            jalali_end = jdatetime.datetime.strptime(end_date_str, "%Y/%m/%d")

            if jalali_start > jalali_end:
                messages.error(request, "لطفاً دقت کنید که “تاریخ شروع” باید قبل از “تاریخ پایان” انتخاب شود")
                # اگر تاریخ نامعتبر بود، فیلتر تاریخ را اعمال نمی‌کنیم
                start_date_str = None
                end_date_str = None
        except ValueError:
            # اگر فرمت تاریخ اشتباه بود، در ادامه کد نادیده گرفته می‌شود
            pass

    #اعمال فیلتر روش پرداخت و وضعیت
    if payment_method:
        payments = payments.filter(payment_method=payment_method)

    if status:
        payments = payments.filter(status=status)

    if start_date_str:
        try:
            # تبدیل تاریخ شمسی ورودی به میلادی
            jalali_start = jdatetime.datetime.strptime(start_date_str, "%Y/%m/%d")
            gregorian_start_dt = jalali_start.togregorian()
            #تاریخ رو با تایم‌زون محلی (تهران) تنظیم می‌کنیم (aware)برای مقایسه صحیح، 
            aware_start_dt = timezone.make_aware(gregorian_start_dt)
            payments = payments.filter(paid_at__gte=aware_start_dt)
        except ValueError:
            pass 

    if end_date_str:
        try:
            jalali_end = jdatetime.datetime.strptime(end_date_str, "%Y/%m/%d")
            # ساعت رو می‌ذاریم رو آخرین لحظه روز (۲۳:۵۹:۵۹) که کل اون روز رو شامل بشه
            gregorian_end_dt = datetime.combine(jalali_end.togregorian().date(), time.max)
            aware_end_dt = timezone.make_aware(gregorian_end_dt)
            payments = payments.filter(paid_at__lte=aware_end_dt)
        except ValueError:
            pass

    paginator = Paginator(payments, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    
    for payment in page_obj:
        if payment.paid_at:
            #  تبدیل تاریخ پرداخت به شمسی
            # زمان رو به تایم لوکال (تهران) برمی‌گردونیم و بعد شمسی می‌کنیم
            local_time = timezone.localtime(payment.paid_at)
            jalali = jdatetime.datetime.fromgregorian(datetime=local_time)
            payment.paid_at_jalali = jalali.strftime("%Y/%m/%d - %H:%M")
        else:
            payment.paid_at_jalali = "-"

        amount_int = int(payment.amount)
        payment.amount_display = f"{amount_int:,}"      
        payment.amount_words = number_to_persian_words(amount_int)

    context = {
        "payments": page_obj,
        "selected_method": payment_method,
        "selected_status": status,
        "selected_start_date": start_date_str, 
        "selected_end_date": end_date_str,
    }

    return render(request, "panel/payment_list.html", context)


#گزارش درامد

# تابع کمکی برای فرمت‌بندی اعداد با کاما
def format_number_with_comma(number):
    if number is None:
        return "0"
    try:
        num_int = int(number)
    except (ValueError, TypeError):
        return str(number) 

    return "{:,}".format(num_int)

@panel_access_required
def income_report(request):

    payments = Payment.objects.filter(status='success', appointment__status='completed')
    package_payments = PackagePayment.objects.filter(status='success')

    today = timezone.localdate()

    #  فیلترهای سریع
    filter_type = request.GET.get('filter')

    if filter_type == 'today':
        payments = payments.filter(paid_at__date=today)
        package_payments = package_payments.filter(created_at__date=today)

    elif filter_type == 'week':
        # شنبه در پایتون = 5
        days_since_saturday = (today.weekday() - 5) % 7
        start_week = today - timedelta(days=days_since_saturday)
        payments = payments.filter(paid_at__date__gte=start_week)
        package_payments = package_payments.filter(created_at__date__gte=start_week)

    elif filter_type == 'month':
        # روز اول ماه شمسی جاری رو پیدا می‌کنیم و بعد واسه دیتابیس میلادی‌اش می‌کنیم.
        jalali_today = jdatetime.date.today()
        jalali_first = jdatetime.date(jalali_today.year, jalali_today.month, 1)
        gregorian_first = jalali_first.togregorian()

        payments = payments.filter(paid_at__date__gte=gregorian_first)
        package_payments = package_payments.filter(created_at__date__gte=gregorian_first)

    elif filter_type == 'year':
        # روز اول فروردین امسال
        jalali_today = jdatetime.date.today()
        jalali_first = jdatetime.date(jalali_today.year, 1, 1)
        gregorian_first = jalali_first.togregorian()

        payments = payments.filter(paid_at__date__gte=gregorian_first)
        package_payments = package_payments.filter(created_at__date__gte=gregorian_first)

    #  بازه دلخواه
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    start_date = None
    end_date = None
    date_error = None 

    # برای اطمینان از فرمت صحیح تاریخ و جلوگیری از خطا
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            payments = payments.filter(paid_at__isnull=False, paid_at__date__gte=start_date)
            package_payments = package_payments.filter(created_at__date__gte=start_date)
        except ValueError:
            pass

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            payments = payments.filter(paid_at__isnull=False, paid_at__date__lte=end_date)
            package_payments = package_payments.filter(created_at__date__lte=end_date)
        except ValueError:
            pass

    #  بررسی منطقی بودن بازه تاریخ
    if start_date and end_date and start_date > end_date:
        date_error = "تاریخ شروع نمی‌تواند بزرگ‌تر از تاریخ پایان باشد!"


    #  فیلتر پرسنل
    staff_id = request.GET.get('staff')
    if staff_id:
        payments = payments.filter(appointment__staff_id=staff_id)
        

    #  فیلتر روش پرداخت
    payment_method = request.GET.get('method')
    if payment_method:
        payments = payments.filter(payment_method=payment_method)
        package_payments = package_payments.filter(payment_method=payment_method)
        
    #کدوم سرویس هم از نظر تعداد و هم مبلغ، پرفروش‌ترین بوده
    #پرداخت‌ها رو بر اساس اسم سرویس گروه‌بندی کن، بعد تعداد و جمع درآمد هر گروه رو حساب کن و در نهایت پرفروش‌ترین رو برگردون.
    top_service = payments.values(
        service_name=F('appointment__service__name')
    ).annotate(
        total_sales=Count('id'),
        total_income=Sum('amount')
    ).order_by('-total_sales').first()


    #  محاسبه درآمد،،جمع کل پولایی که از سرویس‌ها و پکیج‌ها درومده
    #Aggregate یه دیکشنری میده که مقدارش تو کلید total هست
    services_income = payments.aggregate(total=Sum('amount'))['total'] or 0
    packages_income = package_payments.aggregate(total=Sum('amount'))['total'] or 0
    total_income = services_income + packages_income

    #پرسنلی که بیشترین درآمد رو دارن
    #جمع درآمد هر پرسنل رو محاسبه کرده و ۵ نفر اول رو جدا می‌کنیم.
    top_staff = payments.values(
        'appointment__staff__full_name'
    ).annotate(
        total_income=Sum('amount')
    ).order_by('-total_income')

    online_income = (payments.filter(payment_method='online').aggregate(total=Sum('amount'))['total'] or 0) + \
                (package_payments.filter(payment_method='online').aggregate(total=Sum('amount'))['total'] or 0)
                
    cash_income = (payments.filter(payment_method='cash').aggregate(total=Sum('amount'))['total'] or 0) + \
                (package_payments.filter(payment_method='cash').aggregate(total=Sum('amount'))['total'] or 0)
                
    card_income = (payments.filter(payment_method='card').aggregate(total=Sum('amount'))['total'] or 0) + \
                (package_payments.filter(payment_method='card').aggregate(total=Sum('amount'))['total'] or 0)
    
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

        'total_income_formatted': format_number_with_comma(total_income),
        'total_income_words': number_to_persian_words(total_income),

        'services_income_formatted': format_number_with_comma(services_income),
        'services_income_words': number_to_persian_words(services_income),

        'packages_income_formatted': format_number_with_comma(packages_income),
        'packages_income_words': number_to_persian_words(packages_income),

        'online_income_formatted': format_number_with_comma(online_income),
        'online_income_words': number_to_persian_words(online_income),

        'cash_income_formatted': format_number_with_comma(cash_income),
        'cash_income_words': number_to_persian_words(cash_income),

        'card_income_formatted': format_number_with_comma(card_income),
        'card_income_words': number_to_persian_words(card_income),

        'total_payment_income_formatted': format_number_with_comma(total_payment_income),
        'total_payment_income_words': number_to_persian_words(total_payment_income),
        'date_error': date_error,
    }

    if top_service and 'total_income' in top_service:
        context['top_service_income_formatted'] = format_number_with_comma(top_service['total_income'])
        context['top_service_income_words'] = number_to_persian_words(top_service['total_income'])

    if top_staff:
        for staff_data in context['top_staff']:
            if 'total_income' in staff_data:
                staff_data['total_income_formatted'] = format_number_with_comma(staff_data['total_income'])
                staff_data['total_income_words'] = number_to_persian_words(staff_data['total_income'])


    return render(request, 'panel/income_report.html', context)


# برنامه کاری پرسنل
@panel_access_required
def staff_plan(request):

    staffs = Staff.objects.filter(is_active=True)

    staff_id = request.GET.get("staff")
    date_str = request.GET.get("date")

    staff = None
    appointments = None
    is_working_day = True
    today = timezone.localdate()

    # اگه تاریخی انتخاب نشده بود، امروز رو در نظر میگیریم
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    jalali = jdatetime.date.fromgregorian(date=selected_date)
    selected_date_jalali = f"{jalali.year}/{jalali.month:02d}/{jalali.day:02d}"

    #برای دکمه روز قبل و بعد
    prev_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)

    if staff_id:
        staff = get_object_or_404(Staff, id=staff_id)
        
        DAY_MAP = {
            'monday':    'دوشنبه',
            'tuesday':   'سه‌شنبه',
            'wednesday': 'چهارشنبه',
            'thursday':  'پنجشنبه',
            'friday':    'جمعه',
            'saturday':  'شنبه',
            'sunday':    'یکشنبه',
        }
        day_name_en = selected_date.strftime("%A").lower()
        day_name_fa = DAY_MAP.get(day_name_en, '')
    
        # این پرسنل در این روز هفته ایا کار میکنه یا نه
        is_working_day = day_name_fa in staff.work_days

        appointments = Appointment.objects.filter(
            staff=staff,
            appointment_date=selected_date  
        ).order_by('start_time')
        
        confirmed_count = appointments.filter(status='confirmed').count()
        cancelled_count = appointments.filter(status='cancelled').count()
    
    context = {
        "staffs": staffs,
        "staff": staff,
        "appointments": appointments,
        "today": today,
        "selected_date": selected_date,
        "selected_date_jalali": selected_date_jalali,
        "selected_staff": staff_id,
        "is_working_day": is_working_day,
        "confirmed_count": confirmed_count if staff_id else 0,
        "cancelled_count": cancelled_count if staff_id else 0,
        "prev_date": prev_date,
        "next_date": next_date,
    }

    return render(request, "panel/staff_plan.html", context)

