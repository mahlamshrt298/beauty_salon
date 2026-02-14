from django.core.management.base import BaseCommand
from django.utils import timezone
from booking.models import Appointment
from datetime import datetime

class Command(BaseCommand):
    help = "Mark past appointments as completed automatically"

    def handle(self, *args, **kwargs):
        now = timezone.now()

        appointments = Appointment.objects.filter(
            status='confirmed',
            appointment_date__lte=now.date()
        )

        completed_count = 0

        for app in appointments:
            appointment_end = datetime.combine(
                app.appointment_date,
                app.end_time
            )

            if appointment_end < now.replace(tzinfo=None):
                app.status = 'completed'
                app.save(update_fields=['status'])
                completed_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"{completed_count} appointments completed.")
        )
