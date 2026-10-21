"""Celery-задачи для отправки напоминаний."""

from collections import defaultdict

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from .models import SentNotification, Task


@shared_task
def send_reminders(days_ahead: int = 3):
    """
    Находит задачи со сроком в ближайшие days_ahead дней
    и отправляет каждому ответственному одно письмо-дайджест.
    Повторно в тот же день письмо не уходит.
    """
    today = timezone.now().date()

    # Все активные задачи, подходящие по сроку
    active_tasks = Task.objects.filter(status=Task.Status.ACTIVE).select_related(
        "company"
    )

    due_tasks = [t for t in active_tasks if t.is_due(days_ahead)]

    # Исключаем задачи, по которым уже отправлено уведомление сегодня
    already_notified_ids = set(
        SentNotification.objects.filter(
            task__in=due_tasks,
            sent_date=today,
        ).values_list("task_id", flat=True)
    )

    tasks_to_notify = [t for t in due_tasks if t.id not in already_notified_ids]

    if not tasks_to_notify:
        return {"sent": 0, "skipped_duplicate": len(already_notified_ids)}

    # Группируем по email ответственного
    by_email = defaultdict(list)
    for task in tasks_to_notify:
        by_email[task.responsible_email].append(task)

    sent_count = 0
    for email, tasks in by_email.items():
        lines = []
        for task in tasks:
            due_date = task.next_due_date
            if due_date < today:
                status = "ПРОСРОЧЕНО"
            elif due_date == today:
                status = "СЕГОДНЯ"
            else:
                days_left = (due_date - today).days
                status = f"через {days_left} дн."

            lines.append(
                f"  • {task.title} ({task.company.name}) — срок: {due_date} [{status}]"
            )

        body = (
            f"Добрый день!\n\n"
            f"Напоминаем о предстоящих регламентных задачах:\n\n"
            + "\n".join(lines)
            + "\n\nПожалуйста, выполните задачи в срок."
        )

        send_mail(
            subject=f"Напоминание: {len(tasks)} задач(и) требуют внимания",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )

        # Записываем факт отправки
        notifications = [
            SentNotification(task=task, sent_date=today) for task in tasks
        ]
        SentNotification.objects.bulk_create(notifications, ignore_conflicts=True)
        sent_count += 1

    return {
        "sent": sent_count,
        "tasks_notified": len(tasks_to_notify),
        "skipped_duplicate": len(already_notified_ids),
    }
