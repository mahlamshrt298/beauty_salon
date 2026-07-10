from booking.models import Staff,Appointment,Payment
from django.contrib.auth.decorators import login_required
from services_app.models import Category, Service,Subcategory 
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
import json
from accounts.models import DiscountCode , DiscountUsage
from core.models import Package
from django.utils.dateparse import parse_date, parse_time
from django.shortcuts import render, redirect, get_object_or_404
from calendar import monthrange, month_name
import jdatetime
from datetime import time,datetime, date, timedelta
from booking.models import PendingAppointment
from django.db import transaction
from django.db.models import Count
from booking.models import Holiday
from core.models import SalonSettings
from core.models import PackageBooking
from django.db.models import Q
from services_app.models import number_to_persian_words
from core.models import SalonSettings
import sys

#سقف تعداد نوبت‌های همزمان برای هر کاربر
MAX_ACTIVE_APPOINTMENTS_PER_USER = 5

#تابع کمکی برای پیدا کردن پرسنل آزاد برای یک خدمت خاص در یک بازه زمانی مشخص
#از این تابع توی تابع بعدی استفاده میشه
def get_available_staff(service, date, start_time, end_time):

    #کل پرسنل فعال که این سرویس رو انجام میدن
    staff_qs = Staff.objects.filter(
        services=service,
        is_active=True,
        status="active"
    )

    ## حالا اونایی که تو این تاریخ و ساعت تداخل نوبت دارن رو پیدا می‌کنیم
    busy_staff_ids = Appointment.objects.filter(
        service=service,
        appointment_date=date,
        status__in=["pending", "confirmed"],
        start_time__lt=end_time,    # start_time مال نوبت قبلی <= end_time
        end_time__gt=start_time     # end_time مال نوبت قبلی >= start_time
    ).values_list("staff_id", flat=True)

    # در نهایت پرسنل مشغول رو از لیست کل حذف می‌کنیم
    return staff_qs.exclude(id__in=busy_staff_ids)

@login_required
def get_available_staff_ajax(request):
    service_id = request.GET.get("service_id")
    date = request.GET.get("date")          # 1404-10-15
    time = request.GET.get("time")          # 16:00

    if not all([service_id, date, time]):
        return JsonResponse({"staffs": []})

    service = Service.objects.filter(
        id=service_id,
        is_active=True
    ).first()

    if not service:
        return JsonResponse({"staffs": []}, status=404)

    # تبدیل تاریخ شمسی به میلادی
    jy, jm, jd = map(int, date.split("-"))
    date_gregorian = jdatetime.date(jy, jm, jd).togregorian()

    # محاسبه تایم پایان بر اساس تایم شروع و مدت زمان خود سرویس
    start_time = datetime.strptime(time, "%H:%M").time()
    end_time = (
        datetime.combine(date_gregorian, start_time)
        + timedelta(minutes=service.duration_minutes)
    ).time()

    staffs = get_available_staff(
        service=service,
        date=date_gregorian,
        start_time=start_time,
        end_time=end_time
    )

    return JsonResponse({
        "staffs": [
            {
                "id": staff.id,
                "name": staff.full_name,
                "role": staff.role,
            }
            for staff in staffs
        ]
    })

@login_required     #فقط کاربران وارد شده دسترسی خوانهند داشت
def reserve(request):

    # یه فلگ تو سشن می‌ذاریم که بدونیم کاربر تو پروسه رزروه
    request.session["in_booking_flow"] = True

    
    today = timezone.localdate()
    # چک می‌کنیم کاربر بیشتر از حد مجاز نوبت فعال نداشته باشه
    active_appointments_count = Appointment.objects.filter(
        user=request.user,
        status__in=['pending', 'confirmed'],
        appointment_date__gte=today ,
        package_booking__isnull=True    # نوبت‌های پکیجی استثنا هستن
    ).count()

    if active_appointments_count >= MAX_ACTIVE_APPOINTMENTS_PER_USER:
        
        print("DEBUG: Redirect 1 - سقف نوبت ها پر شده است!") # <--- اینجا پرینت کنید
        
        messages.error(
            request,
            "⛔ شما بیش از حد مجاز نوبت فعال دارید. ابتدا نوبت‌های قبلی را مدیریت کنید.",
            extra_tags="front"
        )
        return redirect("accounts:profile")  


    PendingAppointment.objects.get_or_create(
        user=request.user,
        is_completed=False,
        defaults={"step": "select_service"}
    )

    # اگه کاربر از صفحه خرید پکیج اومده باشه، آیدی پکیج رو تو سشن نگه می‌داریم
    package_id = request.GET.get('package')
    #  دریافت service_id از URL در صورتی که کاربر از صفحه خدمات آمده باشد
    service_id = request.GET.get("service")

    selected_package = None

    if package_id:
        selected_package = Package.objects.get(id=package_id)
        request.session['package_id'] = selected_package.id
    
    elif not service_id:
        # اگر نه پکیجی در کار بود و نه مستقیما روی یک سرویس کلیک کرده بود (ورود به صفحه اصلی رزرو)
        # حافظه پکیج‌های قبلی را پاک کن تا رزرو عادی دچار مشکل نشود
        request.session.pop('package_id', None)
        request.session.pop('from_package', None)
        request.session.pop('auto_finalize_package', None)


    # متن راهنمایی بالای صفحه
    reserve_text = "در چند مرحله نوبت خود را رزرو کنید — آنلاین یا پرداخت در محل"

    selected_category = request.GET.get("category")

    selected_service = None
    
    if service_id:
        try:
            # ساپورت آیدی عددی و اسلاگ به صورت همزمان
            if service_id.isdigit():
                selected_service = Service.objects.get(id=int(service_id))
            else:
                selected_service = Service.objects.get(slug=service_id)  #  جستجو با اسلاگ
            
            # سرویس رو تو سشن می‌ذاریم و مستقیم می‌فرستیمش مرحله انتخاب تاریخ
            request.session["selected_service"] = selected_service.id
            return redirect('select_date', service_id=selected_service.id)  # همیشه عدد ارسال می‌شود
        except Service.DoesNotExist:
            selected_service = None
            

    # لیست مراحل برای نوار پیشرفت
    steps = [
        {"number": 1, "title": "انتخاب خدمت", "active": True},  # فرض می‌کنیم کاربر در مرحله اول است
        {"number": 2, "title": "انتخاب تاریخ و ساعت", "active": False},
        {"number": 3, "title": "اطلاعات تماس", "active": False},
        {"number": 4, "title": "پرداخت و تایید", "active": False},
    ]

    # محاسبه عرض هر مرحله (درصد)
    step_width = 100 / len(steps) if len(steps) > 0 else 0

    # گرفتن لیست دسته‌بندی‌ها به همراه زیردسته‌ها و سرویس‌ها برای دراپ‌داون
    categories = Category.objects.prefetch_related('subcategories__services').all().order_by('name')

    #    نمایش صفحه رزرو نوبت
    context = {
        'active_page': 'reserve', 
        'reserve_text': reserve_text,
        'steps': steps,  # ارسال لیست مراحل به تمپلیت
        'step_width': step_width,  # ارسال عرض به تمپلیت
        'categories': categories,  # ارسال دسته‌ها با زیردسته‌ها و خدمات
        "selected_category": selected_category,
        'selected_service': selected_service,
        'selected_package': selected_package,
    }
    return render(request,'reserve.html',context)


@login_required
def select_date(request, service_id , year=None, month=None):
    """
    ویوی مربوط به نمایش تقویم و انتخاب تاریخ وساعت توسط کاربر.
    """

    service = get_object_or_404(Service, id=service_id)
    request.session["selected_service"] = service_id

    # در ویوی select_date، بخش ابتدایی را اینطور تغییر دهید:
    if "from_package" in request.GET:
        # فقط اگر پارامتر در URL بود، سشن را ست کن
        is_from_pkg = request.GET.get("from_package") == "1"
        request.session['from_package'] = is_from_pkg
    # اگر پارامتر نبود، به سشن دست نزن (تا مقدار قبلی حفظ شود)

    if request.session.get("from_package"):
        package_id = request.session.get("package_id")
        
        is_valid_package = False
        if package_id:
            is_valid_package = PackageBooking.objects.filter(
                user=request.user,
                package_id=package_id,
                service=service,
                is_completed=False
            ).exists()

        if not is_valid_package:
            # به جای اینکه ارور بدهیم و کاربر را به پروفایل پرت کنیم،
            # سشن گیر کرده‌ی پکیج را باطل می‌کنیم تا سیستم با این درخواست به عنوان یک «رزرو عادی» رفتار کند.
            request.session.pop('from_package', None)
            request.session.pop('package_id', None)
            request.session.pop('auto_finalize_package', None)

    # آپدیت وضعیت رزرو موقت کاربر به مرحله فعلی
    PendingAppointment.objects.filter(
        user=request.user,
        is_completed=False
    ).update(step="select_date")
        
    # نوار مراحل
    steps = [
        {"number": 1, "title": "انتخاب خدمت", "active": False},
        {"number": 2, "title": "انتخاب تاریخ", "active": True},
        {"number": 3, "title": "اطلاعات مشتری", "active": False},
        {"number": 4, "title": "تایید نهایی", "active": False},
    ]
    step_width = 100 / 4

    #  تاریخ امروز شمسی
    today = jdatetime.date.today()

    # اگه سال و ماه تو URL پاس داده نشده بود، تاریخ امروز رو در نظر می‌گیریم
    current_year = int(year) if year else today.year
    current_month = int(month) if month else today.month

    #  نام ماه
    current_month_name = jdatetime.date.j_months_fa[current_month - 1]

    #  محاسبه ماه قبل
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year

    #  محاسبه ماه بعد
    if current_month == 12:
        next_month = 1
        next_year = current_year + 1
    else:
        next_month = current_month + 1
        next_year = current_year

    #  تعیین تعداد روزهای ماه با روش صحیح
    # پیدا کردن روز اول ماه تا بفهمیم چند تا خونه خالی اول تقویم باید بذاریم
    first_day = jdatetime.date(current_year, current_month, 1)

    # شنبه =0 و جمعه =6
    start_weekday = first_day.weekday()

    empty_days = range(start_weekday)

    first_day_next = jdatetime.date(next_year, next_month, 1)
    num_days = (first_day_next - first_day).days

    #  ساخت لیست روزها
    days_list = list(range(1, num_days + 1))

    #کدوم روزها پر هستن (تعطیلن یا وقتشون پره)
    taken_days = []

    #  اضافه کردن روزهای تعطیل به taken_days

    first_day_jalali = jdatetime.date(current_year, current_month, 1)
    last_day_jalali = jdatetime.date(current_year, current_month, days_list[-1]) if days_list else first_day_jalali
    
    # تبدیل به میلادی می‌کنیم
    first_day_greg = first_day_jalali.togregorian()
    last_day_greg = last_day_jalali.togregorian()
    
    holidays = Holiday.objects.filter(
        date__gte=first_day_greg,
        date__lte=last_day_greg,
        is_active=True
    )
    
    for hol in holidays:
        hol_jalali = jdatetime.date.fromgregorian(date=hol.date)
        if hol_jalali.year == current_year and hol_jalali.month == current_month:
            if hol.is_half_day:
                # نیم‌روز: فقط اون نیمه رو علامت بزن
                pass  
            else:
                # تعطیل کامل
                if hol_jalali.day not in taken_days:
                    taken_days.append(hol_jalali.day)

    #  اضافه کردن روزهای تعطیل هفتگی سالن
    salon_settings = SalonSettings.objects.first()
    if salon_settings and salon_settings.weekend_days:
        persian_weekdays = {
            'شنبه': 0, 'یکشنبه': 1, 'دوشنبه': 2, 
            'سه‌شنبه': 3, 'چهارشنبه': 4, 'پنج‌شنبه': 5, 'جمعه': 6
        }
        
        for day_num in days_list:
            jalali_date = jdatetime.date(current_year, current_month, day_num)
            weekday_num = jalali_date.weekday()  # 0=شنبه, 6=جمعه
            
            # اسم روز هفته رو پیدا می‌کنیم (مثلا "جمعه")
            weekday_name = [k for k, v in persian_weekdays.items() if v == weekday_num][0]
            
            if weekday_name in salon_settings.weekend_days:
                if day_num not in taken_days:
                    taken_days.append(day_num)


    # گرفتن پرسنل‌های فعال مرتبط با این خدمت
    staffs = Staff.objects.filter(
        is_active=True,
        status="active",
        services=service
    )

    # اگه هیچ پرسنلی برای این سرویس پیدا نشد، کاربر رو برمی‌گردونیم مرحله قبل
    if not staffs.exists():
        messages.error(
            request,
            "برای این خدمت هنوز پرسنلی تعریف نشده است.",
            extra_tags="front"
        )
        return redirect("reserve")

    # کل روزهای ماه رو چک می‌کنیم تا ببینیم آیا هیچ تایم خالی پیدا میشه یا نه
    for day in days_list:
        date_gregorian = jdatetime.date(
            current_year, current_month, day
        ).togregorian()

        has_any_free_slot = False

        for staff in staffs:
            # بررسی روز کاری پرسنل
            weekday_fa_raw = jdatetime.date(
                current_year, current_month, day
            ).strftime("%A")

            # حذف فاصله و نیم‌فاصله از روز فعلی
            weekday_fa_clean = weekday_fa_raw.replace("‌", "").replace(" ", "")
            
            # حذف فاصله و نیم‌فاصله از لیست روزهای کاری پرسنل
            staff_work_days_clean = [d.replace("‌", "").replace(" ", "") for d in staff.work_days]

            # اگه پرسنل این روز تعطیله، بی‌خیالش میشیم
            if weekday_fa_clean not in staff_work_days_clean:
                continue

            start_work = datetime.combine(date_gregorian, staff.work_start_time)
            end_work = datetime.combine(date_gregorian, staff.work_end_time)

            duration = service.duration_minutes
            current = start_work

            # شیفت کاری پرسنل رو اسلات به اسلات (بر اساس تایم سرویس) جلو میریم
            #میخاد ببینه حتی یه جای خالی توی این روز هست یا نه،اگر پیدا کرد میره روز بعدی وگرنه میزارش توی روزهای پر
            while current + timedelta(minutes=duration) <= end_work:
                slot_start = current.time()
                slot_end = (current + timedelta(minutes=duration)).time()

                # چک وقت ناهار پرسنل
                if staff.has_lunch_break:
                    if slot_start < staff.lunch_end and slot_end > staff.lunch_start:
                        current += timedelta(minutes=duration)
                        continue

                # چک می‌کنیم تو این اسلات زمانی، نوبت ثبت‌شده‌ای داره یا نه
                conflict = Appointment.objects.filter(
                    appointment_date=date_gregorian,
                    staff=staff,
                    service=service,
                    status__in=['pending', 'confirmed'],
                    start_time__lt=slot_end,
                    end_time__gt=slot_start
                ).exists()

                # اگه تداخل نداشت، یعنی حداقل یه جای خالی تو این روز هست
                if not conflict:
                    has_any_free_slot = True
                    break

                current += timedelta(minutes=duration)
            
            if has_any_free_slot:
                break

        # اگه هیچ جای خالی تو کل پرسنل برای این روز نبود، روز رو می‌بندیم (غیرفعال میشه تو تقویم)
        if not has_any_free_slot:
            taken_days.append(day)

    #پیدا کردن روزهای گذشته
    past_days = []

    for d in days_list:
        date_jalali = jdatetime.date(current_year, current_month, d)
        if date_jalali < today:
            past_days.append(d)

    #نمایش تقویم
    if request.method == "GET":
        context = {
            'service': service,
            'current_year': current_year,
            'current_month': current_month,
            'current_month_name': current_month_name,

            'days_list': days_list,

            'past_days': past_days,

            # ماه قبلی / بعدی
            'prev_year': prev_year,
            'prev_month': prev_month,
            'next_year': next_year,
            'next_month': next_month,

            'today_day': today.day,
            'today_month': today.month,
            'today_year': today.year,

            'taken_days': taken_days,
            'start_weekday': start_weekday,
            'empty_days': empty_days,
            
            'steps': steps,
            'step_width': step_width,
        }

        return render(request, 'select_date.html', context)

    #وقتی کاربر تاریخ و ساعت رو انتخاب و سابمیت می‌کنه
    if request.method == "POST":
         #  اول از همه انتخاب پرسنل
        staff_id = request.POST.get("staff")
        if staff_id:
            request.session["selected_staff"] = int(staff_id)
        elif "staff" in request.POST:
            request.session["selected_staff"] = None    # کاربر گفته "فرقی نمی‌کنه چه پرسنلی باشه"


        appointment_date = request.POST.get("appointment_date")
        start_time = request.POST.get("start_time")
        staff_id = request.POST.get("staff")

        if not appointment_date or not start_time:
            messages.error(request, "لطفاً تاریخ و ساعت را انتخاب کنید.")
            return redirect(request.path)

        try:
            year, month, day = map(int, appointment_date.split('-'))
            jalali_date = jdatetime.date(year, month, day)
        except:
            messages.error(request, "تاریخ نامعتبر است.")
            return redirect(request.path)

        #  چک روزهای تعطیل هفتگی
        #اعتبارسنجی مجدد سمت بک‌اند
        salon_settings = SalonSettings.objects.first()
        if salon_settings and salon_settings.weekend_days:
            persian_weekdays = {
                'شنبه': 0, 'یکشنبه': 1, 'دوشنبه': 2, 
                'سه‌شنبه': 3, 'چهارشنبه': 4, 'پنج‌شنبه': 5, 'جمعه': 6
            }
            
            weekday_num = jalali_date.weekday()
            weekday_name = [k for k, v in persian_weekdays.items() if v == weekday_num][0]
            
            if weekday_name in salon_settings.weekend_days:
                messages.error(request, f'روز {weekday_name} تعطیل هفتگی سالن است.')
                return redirect(request.path)
            
        # ذخیره تو سشن و محاسبه تایم پایان
        request.session["appointment_date"] = appointment_date
        request.session["start_time"] = start_time

        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = start_dt + timedelta(minutes=service.duration_minutes)
        request.session["end_time"] = end_dt.strftime("%H:%M")

        # رفتن به مرحله گرفتن شماره تماس
        return redirect("contact_info")

    return render(request, "select_date.html", {
        "service": service,
        "steps": steps,
        "step_width": step_width,
    })


#تایید اطلاعات و گرفتن شماره تماس/توضیحات مشتری
@login_required
def contact_info(request):

    # دریافت داده‌های قبلی از session
    service_id = request.session.get('selected_service')
    start_time = request.session.get('start_time')
    end_time = request.session.get('end_time')

    appointment_date_jalali = request.session.get('appointment_date')

    appointment_date = None
    appointment_date_fa = None
    weekday_fa = None

    #فرمت‌بندی تاریخ انتخاب شده
    if appointment_date_jalali:
        jy, jm, jd = map(int, appointment_date_jalali.split("-"))

        # تاریخ شمسی
        date_jalali = jdatetime.date(jy, jm, jd)

        appointment_date = date_jalali.togregorian()    # تبدیل به میلادی برای ذخیره تو دیتابیس

        appointment_date_fa = date_jalali.strftime("%Y/%m/%d")      # برای نمایش به کاربر

        # روز هفته فارسی
        weekday_fa = date_jalali.strftime("%A")


    selected_staff_id = request.session.get("selected_staff")
    selected_staff = None
    staff_label = "فرقی ندارد (اولین پرسنل آزاد)"

    # اگه یوزر از وسط راه پریده بود تو این صفحه و دیتای سشن ناقص بود
    if not all([service_id, appointment_date, start_time]):
        messages.error(request, "اطلاعات ناقص است. لطفاً مراحل قبلی را تکمیل کنید.", extra_tags = "front")
        return redirect('reserve')

    try:
        service = Service.objects.get(id=service_id)

        if selected_staff_id:
            try:
                selected_staff = Staff.objects.get(id=selected_staff_id)
                staff_label = selected_staff.full_name
            except Staff.DoesNotExist:
                selected_staff = None
                staff_label = "فرقی ندارد (اولین پرسنل آزاد)"

    except Service.DoesNotExist:
        messages.error(request, "خدمت مورد نظر یافت نشد.", extra_tags = "front")
        return redirect('reserve')

    # آپدیت استپ فعلی در دیتابیس
    PendingAppointment.objects.filter(
        user=request.user,
        is_completed=False
    ).update(step="contact_info")


    if request.method == 'POST':
        phone = request.POST.get('phone')
        notes = request.POST.get('notes', '')

        # ذخیره در session
        request.session['phone'] = phone
        request.session['notes'] = notes

        # اگه رزرو از نوع پکیج بود، نیازی به درگاه پرداخت نیست، مستقیم فاکتور نهایی رو می‌سازیم
        if request.session.get("from_package"):
            request.session["auto_finalize_package"] = True
            request.session.save()
            return redirect('payment_confirm')
        else:
            return redirect('payment_confirm')

    # نوار پیشرفت
    steps = [
        {"number": 1, "title": "انتخاب خدمت", "active": False},
        {"number": 2, "title": "انتخاب تاریخ و ساعت", "active": False},
        {"number": 3, "title": "اطلاعات تماس", "active": True},
        {"number": 4, "title": "پرداخت و تایید", "active": False},
    ]
    step_width = 100 / 4

    #  پیش‌پر کردن شماره تماس از پروفایل (اولویت: سشن > پروفایل)
    phone_value = request.session.get('phone', '')  # اگر قبلاً در این فرآیند وارد کرده
    phone_value = request.user.profile.phone or ''  # از پروفایل بگیر

    context = {
        'active_page': 'reserve',
        'service': service,
        'appointment_date': appointment_date,
        'appointment_date_fa': appointment_date_fa,
        'start_time': start_time,
        'steps': steps,
        'step_width': step_width,
        'service_id': service_id, 
        'selected_staff': selected_staff,
        'staff_label': staff_label,
        'weekday_fa': weekday_fa, 
        'phone_value': phone_value,
    }
    return render(request, 'contact_info.html', context)


@login_required
def payment_confirm(request):
    # چک می‌کنیم آیا کاربر داره از اعتبار پکیجش استفاده می‌کنه یا رزرو عادیه
    from_package = request.session.get("from_package", False)

    print(f"DEBUG: from_package={from_package}, auto_finalize_session={request.session.get('auto_finalize_package')}")


    # اطمینان از اینکه اگر کاربر از پکیج است، auto_finalize حتما فعال باشد
    if from_package:
        request.session["auto_finalize_package"] = True

    discount = None
    discounted_price = None
 
    # بررسی اینکه آیا از قبل کد تخفیفی تو سشن ذخیره شده یا نه
    discount_id = request.session.get("discount_id")
    if discount_id:
        try:
            discount = DiscountCode.objects.get(id=discount_id)
            
        except DiscountCode.DoesNotExist:
            request.session.pop("discount_id", None)
            discounted_price = None

    # دریافت تمام داده‌ها از session
    service_id = request.session.get('selected_service')
    appointment_date_jalali = request.session.get('appointment_date')
    
    # اگه تاریخ نداشتیم یعنی یوزر مستقیم لینک رو باز کرده، پس برش می‌گردونیم
    if not appointment_date_jalali:
        messages.error(request, "تاریخ نوبت مشخص نشده است.", extra_tags="front")
        return redirect("select_date", service_id=service_id)
    
    # تبدیل تاریخ شمسی به میلادی
    jy, jm, jd = map(int, appointment_date_jalali.split("-"))
    date_jalali = jdatetime.date(jy, jm, jd)
    appointment_date_gregorian = jdatetime.date(jy, jm, jd).togregorian()

    start_time = request.session.get('start_time')
    end_time = request.session.get('end_time')
    phone = request.session.get('phone')
    notes = request.session.get('notes', '')

    selected_staff_id = request.session.get("selected_staff")
    selected_staff = None
    staff_label = "فرقی ندارد (اولین پرسنل آزاد)"

    #تبدیل عدد قیمت به حروف
    discounted_price_words = number_to_persian_words(discounted_price) if discounted_price else None

    # نام روز هفته به فارسی
    weekday_fa = date_jalali.strftime("%A")

    # چک امنیتی: اگه متد GET بود و دیتامون ناقصه
    if request.method == "GET":
        if not all([service_id, appointment_date_jalali, start_time, phone]):
            messages.error(request, "اطلاعات ناقص است.", extra_tags = "front")
            return redirect('contact_info')

    try:
        service = Service.objects.get(id=service_id)
        base_price = service.price
        
        """ if from_package and request.method == "GET":
            
            request.POST = request.POST.copy()
            request.POST["final_submit"] = "1"
         """
        
        # پیدا کردن آبجکت پرسنل انتخابی (اگه انتخاب کرده باشه)
        if selected_staff_id:
            try:
                selected_staff = Staff.objects.get(id=selected_staff_id)
                staff_label = selected_staff.full_name
            except Staff.DoesNotExist:
                selected_staff = None
                staff_label = "فرقی ندارد (اولین پرسنل آزاد)"

    except Service.DoesNotExist:
        messages.error(request, "خدمت یافت نشد.", extra_tags = "front")
        return redirect('reserve')

    # نوار پیشرفت
    steps = [
        {"number": 1, "title": "انتخاب خدمت", "active": False},
        {"number": 2, "title": "انتخاب تاریخ و ساعت", "active": False},
        {"number": 3, "title": "اطلاعات تماس", "active": False},
        {"number": 4, "title": "پرداخت و تایید", "active": True},
    ]
    step_width = 100 / 4

    """ if request.session.get("auto_finalize_package"):
        #request.session.pop("auto_finalize_package")

        request.POST = request.POST.copy()
        request.POST["final_submit"] = "1"
        request.method = "POST"
     """
    

    settings = SalonSettings.objects.first()

    """ #  منطق هدایت خودکار برای پکیج 
    if from_package or request.session.get("auto_finalize_package"):
        request.POST = request.POST.copy()
        request.POST["final_submit"] = "1"
        request.method = "POST"
     """
    
    #  اعمال کد تخفیف
    if "apply_discount" in request.POST:

        code = request.POST.get("discount_code")
        if not code:
            messages.error(request, "لطفاً کد تخفیف را وارد کنید.", extra_tags="front")
        else:
            try:
                disc = DiscountCode.objects.get(code=code)

                # اعتبارسنجی‌های مربوط به کد تخفیف
                if DiscountUsage.objects.filter(user=request.user,discount=disc).exists():
                    messages.error(request, "❌ شما قبلاً از این کد تخفیف استفاده کرده‌اید", extra_tags="front")

                elif not disc.is_active:
                    messages.error(request, "این کد تخفیف غیرفعال است ❌", extra_tags="front")

                elif disc.expires_at < timezone.now().date():
                    messages.error(request, "⏰ مهلت استفاده از این کد به پایان رسیده", extra_tags="front")

                else:
                    # اعمال تخفیف و ذخیره آیدیش تو سشن
                    discount = disc
                    #این قیمت پس از اعمال تخفیفه
                    discounted_price = service.price * (100 - disc.percent) / 100
                    # ذخیره‌سازی موقت برای استفاده در ایجاد پرداخت
                    request.session["discount_id"] = disc.id
                    messages.success(request, "کد تخفیف اعمال شد ✅", extra_tags="front")

            except DiscountCode.DoesNotExist:
                messages.error(request, "کد تخفیف نامعتبر.", extra_tags="front")
        
        # حفظ تمام داده‌های سشن
        # رندر مجدد صفحه با قیمت‌های جدید
        context = {
            "discount_percent": discount.percent if discount else None,
            "discounted_price": discounted_price,
            'active_page': 'reserve',
            'service': service,
            'appointment_date_jalali': appointment_date_jalali,
            'start_time': start_time,
            "weekday_fa": weekday_fa,
            'phone': phone,
            'notes': notes,
            'steps': steps,
            'step_width': step_width,
            'selected_staff': selected_staff,
            'staff_label': staff_label,
            'discounted_price_words': discounted_price_words,
            'settings': settings,
        }
        return render(request, "payment_confirm.html", context)
    
    # مشخص می‌کنیم که آیا این یک درخواست ثبت نهایی است یا هدایت خودکار پکیج
    is_auto_finalize = from_package or request.session.get("auto_finalize_package", False)
    is_final_submit = "final_submit" in request.POST or is_auto_finalize

     #  رزرو نهایی
    if is_final_submit:        
        payment_method = request.POST.get('payment_method', 'cash')

        #  جلوگیری از تقلب در صورت غیرفعال بودن پرداخت آنلاین
        if payment_method == "online" and not settings.enable_online_payment:
            messages.error(request, "پرداخت آنلاین در حال حاضر غیرفعال است.", extra_tags="front")
            return redirect("reserve")

        if end_time is None:
            # محاسبه دوباره end_time
            start_dt = datetime.strptime(start_time, "%H:%M")
            duration_minutes = service.duration_minutes
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            end_time = end_dt.strftime("%H:%M")

        #  اعتبارسنجی نهایی: آیا این روز جزو تعطیلات هفتگی سالن است؟
        if settings and settings.weekend_days:
            weekend_list = settings.weekend_days
            if weekday_fa in weekend_list:
                messages.error(request, f"امکان رزرو در روز {weekday_fa} وجود ندارد. این روز جزو تعطیلات هفتگی سالن است.", extra_tags="front")
                return redirect("reserve")

        # چک کردن سقف نوبت‌های فعال کاربر
        today = timezone.localdate()
        active_appointments_count = Appointment.objects.select_for_update().filter(
            user=request.user,
            status__in=['pending', 'confirmed'],
            appointment_date__gte=today  ,
            package_booking__isnull=True 
        ).count()

        if active_appointments_count >= MAX_ACTIVE_APPOINTMENTS_PER_USER:
            messages.error(
                request,
                "⛔ شما به سقف مجاز نوبت فعال رسیده‌اید.",
                extra_tags="front"
            )
            return redirect("reserve")

        # ایجاد نوبت
        with transaction.atomic():
            start_time_obj = datetime.strptime(start_time, "%H:%M").time()
            end_time_obj = datetime.strptime(end_time, "%H:%M").time()

            final_staff = None
            selected_staff_id = request.session.get("selected_staff")

            #حالت اول: پرسنل خاصی رو انتخاب کرده
            if selected_staff_id:    
                try:
                    staff = Staff.objects.get(id=selected_staff_id)

                    #  بررسی روزهای کاری پرسنل
                    if staff.work_days:
                        normalized_weekday = weekday_fa.replace('‌', '').replace(' ', '')
                        normalized_work_days = [day.replace('‌', '').replace(' ', '') for day in staff.work_days]
                        
                        if normalized_weekday not in normalized_work_days:
                            messages.error(request, f"❌ پرسنل انتخابی در روز {weekday_fa} کار نمی‌کند.", extra_tags="front")
                            return redirect('select_date', service_id=service.id)

                    # بررسی تداخل زمانی
                    # آیا تو این تایم پره یا خالی؟
                    conflict_exists = Appointment.objects.filter(
                        staff=staff,
                        appointment_date=appointment_date_gregorian,
                        start_time__lt=end_time_obj,
                        end_time__gt=start_time_obj,
                        status__in=['pending', 'confirmed']
                    ).exists()

                    if conflict_exists:
                        messages.error(request, "❌ این پرسنل در این ساعت آزاد نیست.", extra_tags="front")
                        return redirect('select_date', service_id=service.id)

                    final_staff = staff

                except Staff.DoesNotExist:
                    messages.error(request, "❌ پرسنل انتخابی یافت نشد.", extra_tags="front")
                    return redirect('select_date', service_id=service.id)

            #حالت دوم: پرسنل براش فرقی نداشت (اولین نفر آزاد رو پیدا می‌کنیم)
            else:
                # بررسی اینکه حداقل یک پرسنل آزاد باشد
                staff_candidates = Staff.objects.filter(
                    services=service,
                    is_active=True,
                    status="active"
                )

                for staff in staff_candidates:
                    # چک روز کاری
                    if staff.work_days:
                        normalized_weekday = weekday_fa.replace('‌', '').replace(' ', '')
                        normalized_work_days = [day.replace('‌', '').replace(' ', '') for day in staff.work_days]
                        if normalized_weekday not in normalized_work_days:
                            continue

                    # چک تداخل زمانی
                    conflict = Appointment.objects.filter(
                        staff=staff,
                        appointment_date=appointment_date_gregorian,
                        start_time__lt=end_time_obj,
                        end_time__gt=start_time_obj,
                        status__in=['pending', 'confirmed']
                    ).exists()

                    if not conflict:
                        final_staff = staff
                        break

                if not final_staff:
                    messages.error(
                        request,
                        "❌ متأسفانه هیچ پرسنلی در این ساعت آزاد نیست.",
                        extra_tags="front"
                    )
                    return redirect('select_date', service_id=service.id)

            # مدیریت کم کردن اعتبار از پکیج
            package_id = request.session.get("package_id")
            package_booking_instance = None
            came_from_package = False

            if package_id:
                package_booking_instance = PackageBooking.objects.filter(
                    user=request.user,
                    package_id=package_id,
                    service=service,
                    is_completed=False
                ).first()

                if package_booking_instance:
                    came_from_package = True


            # ثبت رکورد اصلی نوبت تو دیتابیس
            appointment = Appointment.objects.create(
                user=request.user,
                service=service,
                staff=final_staff,
                appointment_date=appointment_date_gregorian,
                start_time=start_time,
                end_time=end_time,
                service_name_snapshot=service.name,     
                status='pending',
                notes=notes,
                phone=phone,
                package_booking=package_booking_instance 
            )

            # اگه پکیج بود، اون آیتم پکیج رو تیک می‌زنیم که استفاده شد
            if package_booking_instance:
                package_booking_instance.is_completed = True
                package_booking_instance.save()

            # چک می‌کنیم آیا کلا پکیج تموم شد یا نه؟
            #  اگر همه سرویس‌های پکیج تکمیل شده، سشن پاک شود
            if package_id:
                remaining = PackageBooking.objects.filter(
                    user=request.user,
                    package_id=package_id,
                    is_completed=False
                ).exists()

                if not remaining:
                    request.session["package_completed"] = True
                    request.session.pop("package_id", None)
                else:
                    request.session["package_completed"] = False      

            # محاسبه قیمت نهایی با احتساب تخفیف احتمالی
            final_price = service.price
            discount = None
            discount_id = request.session.get("discount_id")
            if discount_id:
                try:
                    discount = DiscountCode.objects.get(id=discount_id, is_active=True)
                    if discount.expires_at >= timezone.now().date():
                        final_price = service.price * (100 - discount.percent) / 100
                except DiscountCode.DoesNotExist:
                    discount = None

            # ایجاد پرداخت (اگه پکیج نباشه)
            if not from_package:
                Payment.objects.create(
                    appointment=appointment,
                    amount=final_price,
                    payment_method=payment_method,
                    status='pending' if payment_method == 'online' else 'success',
                    paid_at=timezone.now() if payment_method != 'online' else None 
                )

            # ثبت سابقه استفاده از کد تخفیف
            if discount:
                DiscountUsage.objects.create(
                    user=request.user,
                    discount=discount
                )

            # بستن وضعیت نوبت معلق
            PendingAppointment.objects.filter(
                user=request.user,
                is_completed=False
            ).update(is_completed=True)


            # پاک کردن session
            for key in ['selected_service', 'appointment_date', 'start_time', 'end_time', 'phone', 'notes','discount_id','discounted_price','in_booking_flow', 'from_package', 'auto_finalize_package']:
                request.session.pop(key, None)

            messages.success(request, "نوبت شما با موفقیت رزرو شد! 🎉", extra_tags = "front")
            
             # ریدایرکت به صفحه تایید نهایی همراه با کد رهگیری
            if came_from_package:
                return redirect(f"/booking/confirmation/{appointment.tracking_code}/?from_package=1")
            else:
                # یا به صفحه جزئیات نوبت
                return redirect('confirmation', tracking_code=appointment.tracking_code)
         

   # GET request یا اولین نمایش صفحه
    context = {
        "discount_percent": discount.percent if discount else None,
        "discounted_price": discounted_price,
        'active_page': 'reserve',
        'service': service,
        'appointment_date_jalali': appointment_date_jalali,
        'start_time': start_time,
        "weekday_fa": weekday_fa,
        'phone': phone,
        'notes': notes,
        'steps': steps,
        'step_width': step_width,
        'selected_staff': selected_staff,
        'staff_label': staff_label,
        'discounted_price_words': discounted_price_words,
        'settings': settings,
    }
    return render(request, 'payment_confirm.html', context)


#صفحه نمایش موفقیت‌آمیز بودن رزرو (فاکتور نهایی)
@login_required
def confirmation(request, tracking_code):

    #دریافت نوبت بر اساس کد پیگیری
    appointment = get_object_or_404(
        Appointment,
        tracking_code=tracking_code,
        user=request.user
    )

    #  گرفتن اطلاعات پرداخت
    payment = Payment.objects.filter(appointment=appointment).first()

    from_package = appointment.package_booking is not None

    package = None
    if from_package:
        package = appointment.package_booking.package


    #  تبدیل تاریخ میلادی ذخیره‌شده به شمسی
    g_date = appointment.appointment_date
    j_date = jdatetime.date.fromgregorian(date=g_date)
    weekday_fa = j_date.strftime("%A")

    # محاسبه قیمت و تخفیف برای نمایش در فاکتور
    original_price = appointment.service.price if appointment.service else 0
    final_price = payment.amount if payment else original_price
    final_price_words = number_to_persian_words(final_price)

    discount_percent = None
    discount_amount = 0
    
    if payment and original_price > 0:
        # میزان تخفیف(مقداری که کم شده از مبلغ)
        discount_amount = original_price - final_price
        if discount_amount > 0:
            discount_percent = round((discount_amount / original_price) * 100, 2)

    # چک کردن وضعیت اتمام پکیج (و پاک کردنش از سشن)
    package_completed = request.session.pop("package_completed", False)

    # تشخیص اینکه یوزر از پنل کاربریش اومده فاکتور رو ببینه یا تازه رزرو کرده
    from_profile = request.GET.get('from_profile', '0') == '1'

    context = {
        'appointment': appointment,
        'payment': payment,
        'original_price': original_price,
        'final_price': final_price,
        'discount_percent': discount_percent,
        'discount_amount': discount_amount,
        "fa_day": j_date.day,
        "fa_month": jdatetime.date.j_months_fa[j_date.month - 1],  #نام ماه
        "fa_year": j_date.year,  # تاریخ کامل
        'tracking_code': tracking_code,
        'active_page': 'reserve',
        'fa_weekday': weekday_fa,
        "from_package": from_package,
        "package_completed": package_completed,
        "package": package,
        "from_profile": from_profile,
        "final_price_words": final_price_words,
    }
    return render(request,'confirmation.html',context)


@login_required
def get_available_times(request):
    """بارگذاری ساعت‌های در دسترس برای یک روز خاص"""

    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    day = request.GET.get('day')
    month = request.GET.get('month')
    year = request.GET.get('year')
    service_id = request.session.get('selected_service')

    if not all([day, month, year, service_id]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    try:
        service = Service.objects.filter(
            id=service_id,
            is_active=True
        ).first()

        if not service:
            return JsonResponse({'error': 'Invalid service'}, status=404)

        date_gregorian =  jdatetime.date(int(year), int(month), int(day)).togregorian()
    except (ValueError, Service.DoesNotExist):
        return JsonResponse({'error': 'Invalid date or service'}, status=400)

    # دریافت تنظیمات سالن (اولویت اصلی) (ساعت کاری و ناهار)
    salon_settings = SalonSettings.objects.first()
    
    if salon_settings:
        # ساعت کاری سالن
        start_work = salon_settings.open_time
        end_work = salon_settings.close_time
        
        # تنظیمات ناهار سالن
        has_salon_lunch = salon_settings.has_salon_lunch_break
        salon_lunch_start = salon_settings.salon_lunch_start
        salon_lunch_end = salon_settings.salon_lunch_end
    else:
        # فرآیند پیش‌فرض اگر تنظیمات وجود نداشت
        start_work = time(8, 0)
        end_work = time(18, 0)
        has_salon_lunch = True
        salon_lunch_start = time(13, 0)
        salon_lunch_end = time(14, 0)

    #  بررسی تعطیلی
    # چک کردن تقویم تعطیلات ادمین
    holiday = Holiday.objects.filter(
        date=date_gregorian,
        is_active=True
    ).first()

    if holiday:
        # اگر تعطیلی نیم‌روز باشد، فقط بازه مربوطه را برگردان
        if holiday.is_half_day:
            if holiday.half_day_period == 'morning':
                
                # فقط صبح آزاد است
                start_work = time(8, 0) # تا ساعت 12 ظهر
                end_work = time(12, 0)
            else:  # afternoon
                # فقط بعدازظهر آزاد است
                start_work = time(14, 0) # از ساعت 2 بعدازظهر
                end_work = time(18, 0)  
             # نیم‌روز = بدون ناهار
            has_salon_lunch = False
        else:
            # تعطیل کامل - هیچ ساعتی آزاد نیست
            return JsonResponse({'times': [], 'is_holiday': True, 'holiday_title': holiday.title})
        
    #  مدت زمان خدمت
    duration = service.duration_minutes

    start_datetime = datetime.combine(date_gregorian, start_work)
    end_datetime = datetime.combine(date_gregorian, end_work)

     #   دریافت روز هفته فارسی برای بررسی روز کاری پرسنل
    j_date = jdatetime.date.fromgregorian(date=date_gregorian)
    weekday_fa = j_date.strftime("%A")
    # مهم: اسپیس و نیم‌فاصله‌ها رو پاک میکنیم که مشکل تایپی تو دیتابیس باعث باگ نشه
    weekday_fa_clean = weekday_fa.replace("‌", "").replace(" ", "")

    #   دریافت پرسنل‌های فعال برای این خدمت که در این روز کار می‌کنند
    staffs = Staff.objects.filter(
        services=service,
        is_active=True,
        status="active"
    )

    # فیلتر کردن پرسنل‌هایی که در این روز هفته کار می‌کنند 
    valid_staffs = []
    for staff in staffs:
        staff_work_days_clean = [d.replace("‌", "").replace(" ", "") for d in staff.work_days]
        if weekday_fa_clean in staff_work_days_clean:
            valid_staffs.append(staff)
            
    staffs = valid_staffs

    #   دریافت تمام نوبت‌های پرسنل‌ها در این تاریخ (برای هر خدمتی) تا تداخل‌ها دربیاد
    busy_intervals = {}
    if staffs:
        appointments = Appointment.objects.filter(
            staff__in=staffs,
            appointment_date=date_gregorian,
            status__in=['pending', 'confirmed']
        ).values('staff_id', 'start_time', 'end_time')
        
        for appt in appointments:
            staff_id = appt['staff_id']
            if staff_id not in busy_intervals:
                busy_intervals[staff_id] = []
            busy_intervals[staff_id].append((appt['start_time'], appt['end_time']))


    #   محاسبه تاریخ امروز در تایم‌زون ایران
    #برای جلوگیری از رزرو در گذشته
    now = timezone.localtime(timezone.now())
    today = now.date()
    is_today = (date_gregorian == today)
    
    #   محاسبه زمان مینیمم برای امروز (با بافر 60 دقیقه)
    min_time_for_today = None
    if is_today:
        # کاربر نتونه واسه 5 دقیقه دیگه وقت بگیره، حداقل 1 ساعت به سالن وقت بده
        now_plus_buffer = now + timedelta(minutes=60)  # بافر 60 دقیقه
        min_time_for_today = now_plus_buffer.time()

    available_times = []
    current=start_datetime

    # حلقه اصلی تولید اسلات‌های زمانی
    while current + timedelta(minutes=duration) <= end_datetime:
        slot_start = current.time()
        slot_end = (current + timedelta(minutes=duration)).time()

         #   فیلتر ناهار سالن (فقط اگر نیم‌روز نباشد)
         # تایم ناهار رو رد کن
        if has_salon_lunch and not (holiday and holiday.is_half_day):
            if not (slot_end <= salon_lunch_start or slot_start >= salon_lunch_end):
                current += timedelta(minutes=duration)
                continue

        #   فیلتر ساعت‌های گذشته فقط برای امروز
        # تایم‌های سوخته امروز رو رد کن
        if is_today and min_time_for_today and slot_start < min_time_for_today:
            current += timedelta(minutes=duration)
            continue

        #  بررسی وجود حداقل یک پرسنل آزاد برای این بازه زمانی
        slot_available = False
        for staff in staffs:
            # بررسی اینکه بازه زمانی در ساعات کاری پرسنل باشد
            
            if slot_start < staff.work_start_time or slot_end > staff.work_end_time:
                continue
            
            # بررسی تداخل با نوبت‌های موجود پرسنل (در هر خدمتی)
            staff_busy = busy_intervals.get(staff.id, [])
            has_conflict = any(
                slot_start < busy_end and slot_end > busy_start
                for busy_start, busy_end in staff_busy
            )

            # اگر پرسنل آزاد بود، این بازه زمانی قابل رزرو است
            if not has_conflict:
                slot_available = True
                break

        #  اضافه کردن بازه زمانی اگر حداقل یک پرسنل آزاد وجود داشت
        if slot_available:
            available_times.append(current.strftime("%H:%M"))
        else:
            print(f"❌ فیلتر شد (عدم وجود پرسنل آزاد): {slot_start}", flush=True)

        current += timedelta(minutes=duration)

    
    return JsonResponse({'times': available_times , 'is_holiday': bool(holiday),
        'holiday_title': holiday.title if holiday else None})

@login_required
def select_date_from_package(request, package_id):
    # فلوی رزرو وقتی کاربر از روی یه پکیجی که خریده میخواد وقت بگیره
    if not request.session.get('package_paid'):
        messages.error(request, "ابتدا باید هزینه پکیج را پرداخت کنید")
        return redirect('home')

    package = get_object_or_404(Package, id=package_id)
    services = package.service.all()

    if not services.exists():
        messages.error(request, "این پکیج خدمتی ندارد")
        return redirect("home")

    #  ساخت رکورد برای هر سرویس داخل پکیج (اگر قبلاً ساخته نشده)
     # اگه بار اولشه روی این پکیج کلیک میکنه، رکورد استفاده‌های پکیجش رو میسازیم
    for service in services:
        PackageBooking.objects.get_or_create(
            user=request.user,
            package=package,
            service=service
        )

    #  گرفتن وضعیت رزرو هر سرویس
    bookings = PackageBooking.objects.filter(
        user=request.user,
        package=package
    ).select_related('service')

    # اگر همه سرویس‌ها تکمیل شده‌اند اجازه رزرو مجدد نده
    # اگه کل سهمیه پکیج رو سوزونده بود
    if bookings.filter(is_completed=False).count() == 0:
        messages.info(request, "تمام خدمات این پکیج قبلاً رزرو شده‌اند ✅")
        return redirect("accounts:profile")


    total_services = bookings.count()
    completed_services = bookings.filter(is_completed=True).count()

    salon_settings = SalonSettings.objects.first()

    # ایدی پکیج رو میذاریم تو سشن تا تو ویوی پرداخت (payment_confirm) بفهمیم پول نباید بگیریم
    request.session['package_id'] = package.id 
    request.session['from_package'] = True

    return render(request, "package_services.html", {
        "package": package,
        "bookings": bookings,
        "salon_settings" : salon_settings,
        "total_services": total_services,
        "completed_services": completed_services,
    })

@login_required
def exit_booking_flow(request):
    """پاک کردن سشن وقتی کاربر از رزرو خارج می‌شود"""
    if request.method == 'POST':
        keys_to_clear = [
            'selected_service', 'appointment_date', 'start_time', 
            'end_time', 'phone', 'notes', 'discount_id', 
            'selected_staff', 'in_booking_flow', 'package_id'
        ]
        
        for key in keys_to_clear:
            request.session.pop(key, None)
        
       # پاک کردن نوبت‌های نصفه نیمه از دیتابیس
        PendingAppointment.objects.filter(
            user=request.user,
            is_completed=False
        ).delete()
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)
