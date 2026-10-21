"""Тесты модели Task.is_due и mark_completed."""

from datetime import date, timedelta

import pytest
from django.utils import timezone

from tasks.models import Company, Task


@pytest.fixture
def company(db):
    return Company.objects.create(name="ООО Тест")


def _make_task(company, last_completed, cycle_days=90, status=Task.Status.ACTIVE):
    return Task.objects.create(
        title="Продлить SSL",
        company=company,
        responsible_email="admin@example.com",
        cycle_days=cycle_days,
        last_completed_date=last_completed,
        status=status,
    )


class TestIsDue:
    """Тесты метода Task.is_due(days_ahead)."""

    def test_due_today(self, company):
        """Задача со сроком сегодня — is_due возвращает True."""
        today = timezone.now().date()
        task = _make_task(company, today - timedelta(days=90), cycle_days=90)
        assert task.next_due_date == today
        assert task.is_due(days_ahead=3) is True

    def test_due_in_3_days(self, company):
        """Задача со сроком через 3 дня — граница, is_due(3) = True."""
        today = timezone.now().date()
        task = _make_task(company, today - timedelta(days=87), cycle_days=90)
        assert task.next_due_date == today + timedelta(days=3)
        assert task.is_due(days_ahead=3) is True

    def test_due_in_4_days(self, company):
        """Задача со сроком через 4 дня — за границей, is_due(3) = False."""
        today = timezone.now().date()
        task = _make_task(company, today - timedelta(days=86), cycle_days=90)
        assert task.next_due_date == today + timedelta(days=4)
        assert task.is_due(days_ahead=3) is False

    def test_overdue(self, company):
        """Просроченная задача — is_due всегда True."""
        today = timezone.now().date()
        task = _make_task(company, today - timedelta(days=100), cycle_days=90)
        assert task.next_due_date < today
        assert task.is_due(days_ahead=3) is True

    def test_far_future(self, company):
        """Задача далеко в будущем — is_due = False."""
        today = timezone.now().date()
        task = _make_task(company, today, cycle_days=90)
        assert task.next_due_date == today + timedelta(days=90)
        assert task.is_due(days_ahead=3) is False

    def test_paused_task_not_due(self, company):
        """Приостановленная задача не подходит по сроку."""
        today = timezone.now().date()
        task = _make_task(
            company,
            today - timedelta(days=90),
            cycle_days=90,
            status=Task.Status.PAUSED,
        )
        assert task.is_due(days_ahead=3) is False

    def test_due_in_1_day(self, company):
        """Задача со сроком завтра — is_due(3) = True."""
        today = timezone.now().date()
        task = _make_task(company, today - timedelta(days=89), cycle_days=90)
        assert task.next_due_date == today + timedelta(days=1)
        assert task.is_due(days_ahead=3) is True

    def test_custom_days_ahead(self, company):
        """is_due с кастомным days_ahead."""
        today = timezone.now().date()
        task = _make_task(company, today - timedelta(days=83), cycle_days=90)
        # next_due = today + 7
        assert task.is_due(days_ahead=7) is True
        assert task.is_due(days_ahead=6) is False


class TestMarkCompleted:
    """Тесты метода mark_completed."""

    def test_mark_completed_shifts_date(self, company):
        """mark_completed сдвигает last_completed_date на сегодня."""
        today = timezone.now().date()
        task = _make_task(company, today - timedelta(days=90), cycle_days=90)

        task.mark_completed()
        task.refresh_from_db()

        assert task.last_completed_date == today
        assert task.status == Task.Status.ACTIVE
        assert task.next_due_date == today + timedelta(days=90)

    def test_mark_completed_makes_not_due(self, company):
        """После mark_completed задача больше не is_due."""
        today = timezone.now().date()
        task = _make_task(company, today - timedelta(days=90), cycle_days=90)
        assert task.is_due() is True

        task.mark_completed()
        task.refresh_from_db()

        assert task.is_due() is False


class TestNextDueDate:
    """Тесты свойства next_due_date."""

    def test_next_due_date_calculation(self, company):
        task = _make_task(
            company,
            date(2024, 1, 1),
            cycle_days=30,
        )
        assert task.next_due_date == date(2024, 1, 31)
