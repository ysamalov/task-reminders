from datetime import timedelta

from django.db import models
from django.utils import timezone


class Company(models.Model):
    name = models.CharField("Название компании", max_length=255)

    class Meta:
        verbose_name = "Компания"
        verbose_name_plural = "Компании"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Task(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Активна"
        COMPLETED = "completed", "Выполнена"
        PAUSED = "paused", "Приостановлена"

    title = models.CharField("Название задачи", max_length=255)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="Компания",
    )
    responsible_email = models.EmailField("Email ответственного")
    cycle_days = models.PositiveIntegerField("Периодичность (дни)")
    last_completed_date = models.DateField("Дата последнего выполнения")
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ["company", "title"]

    def __str__(self):
        return f"{self.title} ({self.company})"

    @property
    def next_due_date(self):
        """Дата следующего выполнения."""
        return self.last_completed_date + timedelta(days=self.cycle_days)

    def is_due(self, days_ahead: int = 3) -> bool:
        """
        Возвращает True, если задача подходит по сроку:
        срок наступает в ближайшие days_ahead дней (включительно)
        или уже просрочен.
        Неактивные задачи не считаются подходящими.
        """
        if self.status != self.Status.ACTIVE:
            return False
        today = timezone.now().date()
        return self.next_due_date <= today + timedelta(days=days_ahead)

    def mark_completed(self):
        """Отмечает задачу выполненной и сдвигает следующий срок."""
        self.last_completed_date = timezone.now().date()
        self.status = self.Status.ACTIVE
        self.save(update_fields=["last_completed_date", "status"])


class SentNotification(models.Model):
    """Запись о том, что уведомление по задаче уже отправлено в этот день."""

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="Задача",
    )
    sent_date = models.DateField("Дата отправки")

    class Meta:
        verbose_name = "Отправленное уведомление"
        verbose_name_plural = "Отправленные уведомления"
        unique_together = ("task", "sent_date")

    def __str__(self):
        return f"Уведомление: {self.task} — {self.sent_date}"
