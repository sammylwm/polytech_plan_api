from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Deadline, DeadlineAttachment, Group, SessionTask


@admin.register(Group)
class GroupAdmin(ModelAdmin):
    search_fields = ("name",)


@admin.register(Deadline)
class DeadlineAdmin(ModelAdmin):
    list_display = ("date", "subject", "group", "deadline")
    list_filter = ("date", "group")
    search_fields = ("subject", "deadline", "group__name")
    date_hierarchy = "date"


@admin.register(SessionTask)
class SessionTaskAdmin(ModelAdmin):
    list_display = ("subject", "group", "semester", "due_date")
    list_filter = ("semester", "group")
    search_fields = ("subject", "text", "group__name")


@admin.register(DeadlineAttachment)
class DeadlineAttachmentAdmin(ModelAdmin):
    list_display = ("name", "deadline", "size")
    search_fields = ("name", "deadline__subject", "deadline__group__name")
