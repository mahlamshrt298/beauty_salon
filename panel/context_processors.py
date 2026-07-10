from django.utils import timezone
from datetime import timedelta
from booking.models import Appointment

#آمار نوبت‌ها رو به صورت سراسری به همه تمپلیت‌ها پاس بدیم
def appointment_counts(request):
    if not request.user.is_authenticated:
        return {}
    
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)
    
    return {
        'today_count': Appointment.objects.filter(appointment_date=today).count(),
        'tomorrow_count': Appointment.objects.filter(appointment_date=tomorrow).count(),
    }
