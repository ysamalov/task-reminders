from django.contrib import admin
from django.utils import timezone

from .models import Company, SentNotification, Task


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.action(description="Отметить как выполненные")
def mark_tasks_completed(modeladmin, request, queryset):
    today = timezone.now().date()
    for task in queryset:
        task.last_completed_date = today
        task.status = Task.Status.ACTIVE
        task.save(update_fields=["last_completed_date", "status"])


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "responsible_email",
        "cycle_days",
        "last_completed_date",
        "next_due_date",
        "status",
    )
    list_filter = ("status", "company")
    search_fields = ("title", "responsible_email")
    actions = [mark_tasks_completed]


@admin.register(SentNotification)
class SentNotificationAdmin(admin.ModelAdmin):
    list_display = ("task", "sent_date")
    list_filter = ("sent_date",)
