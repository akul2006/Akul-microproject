from django.apps import AppConfig
import threading
import time
import os
import datetime


class AkulConfig(AppConfig):
    name = 'akul'

    def ready(self):
        if os.environ.get('RUN_MAIN', None) != 'true':
            return
            
        thread = threading.Thread(target=self.run_daily_overdue_checks, daemon=True)
        thread.start()

    def run_daily_overdue_checks(self):
        from akul.models import Circulation, Penalty, LibrarySettings, Notification, EmailLog
        from django.core.mail import send_mail

        while True:
            try:
                today = datetime.date.today()
                tomorrow = today + datetime.timedelta(days=1)
                lib_settings = LibrarySettings.objects.first() or LibrarySettings.objects.create()

                # 1. Notify for books due tomorrow
                approaching_due = Circulation.objects.filter(status='issued', due_date=tomorrow)
                for circ in approaching_due:
                    subject = "Library Reminder: Book Due Tomorrow"
                    message = f"Dear {circ.student.name},\n\nThis is a friendly reminder that the book '{circ.book.title}' is due tomorrow ({circ.due_date}).\nPlease return it to avoid late fees.\n\nRegards,\n{lib_settings.library_name}"
                    
                    if getattr(lib_settings, 'enable_emails', True):
                        send_mail(subject, message, None, [circ.student.email], fail_silently=True)
                        try:
                            EmailLog.objects.create(recipient=circ.student.email, subject=subject, message=message)
                        except Exception:
                            pass
                        print(f"[BACKGROUND TASK] Reminder sent to {circ.student.email}")
                    
                    notif_msg = f"Reminder: '{circ.book.title}' issued to {circ.student.name} is due tomorrow."
                    if not Notification.objects.filter(message=notif_msg, created_at__date=today).exists():
                        Notification.objects.create(message=notif_msg)

                # 2. Process overdue books
                overdue_circulations = Circulation.objects.filter(status='issued', due_date__lt=today)
                for circ in overdue_circulations:
                    days_overdue = (today - circ.due_date).days
                    daily_fine = float(lib_settings.penalty_per_day)
                    total_fine = days_overdue * daily_fine
                    
                    penalty, created = Penalty.objects.update_or_create(
                        student=circ.student, book=circ.book, due_date=circ.due_date, status='unpaid',
                        defaults={'days_overdue': days_overdue, 'amount': total_fine, 'reason': f"Overdue: {circ.book.title}"}
                    )

                    if created or days_overdue % 3 == 0:
                        subject = f"Overdue Notice & Penalty Applied: {circ.book.title}"
                        message = f"Dear {circ.student.name},\n\nYour borrowed book '{circ.book.title}' is now {days_overdue} days overdue.\nA penalty of ₹{total_fine} has been applied.\n\nPlease return the book.\n\nRegards,\n{lib_settings.library_name}"
                        
                        if getattr(lib_settings, 'enable_emails', True):
                            send_mail(subject, message, None, [circ.student.email], fail_silently=True)
                            try:
                                EmailLog.objects.create(recipient=circ.student.email, subject=subject, message=message)
                            except Exception:
                                pass
                            print(f"[BACKGROUND TASK] Overdue notice sent to {circ.student.email}")
                        
                        notif_msg = f"Overdue: '{circ.book.title}' issued to {circ.student.name} is {days_overdue} days overdue."
                        if not Notification.objects.filter(message=notif_msg, created_at__date=today).exists():
                            Notification.objects.create(message=notif_msg)
                            
                # Clean up old notifications (keep last 50)
                count = Notification.objects.count()
                if count > 50:
                    last_ids = Notification.objects.order_by('-created_at').values_list('id', flat=True)[:50]
                    Notification.objects.exclude(id__in=list(last_ids)).delete()
            except Exception as e:
                print(f"[BACKGROUND TASK] Error: {e}")

            # Pause the thread for 24 hours (86400 seconds) before running again
            time.sleep(86400)
