"""Тесты Celery-задачи send_reminders."""

from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from tasks.models import Company, SentNotification, Task
from tasks.tasks import send_reminders


@pytest.fixture
def company(db):
    return Company.objects.create(name="ООО Альфа")


@pytest.fixture
def company2(db):
    return Company.objects.create(name="ООО Бета")


def _make_task(company, email, days_ago, cycle_days=90, status=Task.Status.ACTIVE):
    """Создаёт задачу с last_completed_date = сегодня - days_ago."""
    today = timezone.now().date()
    return Task.objects.create(
        title=f"Задача ({company.name})",
        company=company,
        responsible_email=email,
        cycle_days=cycle_days,
        last_completed_date=today - timedelta(days=days_ago),
        status=status,
    )


class TestSendReminders:
    """Тесты задачи отправки напоминаний."""

    def test_sends_email_for_due_task(self, company):
        """Отправляет письмо для задачи со сроком в 3 дня."""
        _make_task(company, "user@example.com", days_ago=87, cycle_days=90)

        result = send_reminders(days_ahead=3)

        assert result["sent"] == 1
        assert result["tasks_notified"] == 1
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["user@example.com"]
        assert "Задача" in mail.outbox[0].body

    def test_no_email_for_future_task(self, company):
        """Не отправляет письмо для задачи далеко в будущем."""
        _make_task(company, "user@example.com", days_ago=10, cycle_days=90)

        result = send_reminders(days_ahead=3)

        assert result["sent"] == 0
        assert len(mail.outbox) == 0

    def test_digest_groups_by_email(self, company, company2):
        """Один email-дайджест на одного ответственного."""
        email = "admin@example.com"
        _make_task(company, email, days_ago=90, cycle_days=90)
        _make_task(company2, email, days_ago=60, cycle_days=60)

        result = send_reminders(days_ahead=3)

        assert result["sent"] == 1  # Одно письмо
        assert result["tasks_notified"] == 2  # Две задачи
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [email]
        # Обе задачи упоминаются в теле
        assert "ООО Альфа" in mail.outbox[0].body
        assert "ООО Бета" in mail.outbox[0].body

    def test_separate_emails_for_different_recipients(self, company, company2):
        """Разные ответственные получают разные письма."""
        _make_task(company, "user1@example.com", days_ago=90, cycle_days=90)
        _make_task(company2, "user2@example.com", days_ago=60, cycle_days=60)

        result = send_reminders(days_ahead=3)

        assert result["sent"] == 2
        assert len(mail.outbox) == 2
        recipients = {m.to[0] for m in mail.outbox}
        assert recipients == {"user1@example.com", "user2@example.com"}

    def test_no_duplicate_on_same_day(self, company):
        """Повторный вызов в тот же день не отправляет дубль."""
        _make_task(company, "user@example.com", days_ago=90, cycle_days=90)

        result1 = send_reminders(days_ahead=3)
        assert result1["sent"] == 1
        assert len(mail.outbox) == 1

        result2 = send_reminders(days_ahead=3)
        assert result2["sent"] == 0
        assert result2["skipped_duplicate"] == 1
        assert len(mail.outbox) == 1  # Не увеличилось

    def test_notification_record_created(self, company):
        """После отправки создаётся запись SentNotification."""
        task = _make_task(company, "user@example.com", days_ago=90, cycle_days=90)
        today = timezone.now().date()

        send_reminders(days_ahead=3)

        assert SentNotification.objects.filter(
            task=task, sent_date=today
        ).exists()

    def test_paused_task_ignored(self, company):
        """Приостановленные задачи не получают уведомлений."""
        _make_task(
            company,
            "user@example.com",
            days_ago=90,
            cycle_days=90,
            status=Task.Status.PAUSED,
        )

        result = send_reminders(days_ahead=3)

        assert result["sent"] == 0
        assert len(mail.outbox) == 0

    def test_overdue_task_gets_notification(self, company):
        """Просроченная задача получает уведомление с пометкой."""
        _make_task(company, "user@example.com", days_ago=100, cycle_days=90)

        result = send_reminders(days_ahead=3)

        assert result["sent"] == 1
        assert "ПРОСРОЧЕНО" in mail.outbox[0].body

    def test_due_today_label(self, company):
        """Задача со сроком сегодня получает пометку СЕГОДНЯ."""
        _make_task(company, "user@example.com", days_ago=90, cycle_days=90)

        result = send_reminders(days_ahead=3)

        assert result["sent"] == 1
        assert "СЕГОДНЯ" in mail.outbox[0].body

    def test_empty_when_no_tasks(self, db):
        """Без задач ничего не отправляется."""
        result = send_reminders(days_ahead=3)
        assert result["sent"] == 0
        assert len(mail.outbox) == 0
