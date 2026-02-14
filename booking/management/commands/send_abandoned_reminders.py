from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from booking.models import PendingAppointment

class Command(BaseCommand):
    help = "Send reminder for abandoned bookings"

    def handle(self, *args, **kwargs):
        threshold = timezone.now() - timedelta(hours=1)

        pendings = PendingAppointment.objects.filter(
            is_completed=False,
            last_activity__lt=threshold,
            user__profile__reminder_enabled=True
        )

        for p in pendings:
            # فعلاً فقط لاگ
            self.stdout.write(
                f"Reminder should be sent to {p.user.email}"
            )
