from django.contrib import admin

from .models import Deadline, DeadlineAttachment, Group, SessionTask


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Deadline)
class DeadlineAdmin(admin.ModelAdmin):
    list_display = ("date", "subject", "group", "deadline")
    list_filter = ("date", "group")
    search_fields = ("subject", "deadline", "group__name")
    date_hierarchy = "date"


@admin.register(SessionTask)
class SessionTaskAdmin(admin.ModelAdmin):
    list_display = ("subject", "group", "semester", "due_date")
    list_filter = ("semester", "group")
    search_fields = ("subject", "text", "group__name")


@admin.register(DeadlineAttachment)
class DeadlineAttachmentAdmin(admin.ModelAdmin):
    list_display = ("name", "deadline", "size")
    search_fields = ("name", "deadline__subject", "deadline__group__name")
