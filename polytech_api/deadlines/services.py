import unicodedata
from datetime import date
from typing import Literal

from django.db import transaction

from .ai import reconcile_homework
from .models import Deadline, Group


DeadlineStatus = Literal["created", "updated", "unchanged"]


def normalize_text(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split()).rstrip(".!? ")


@transaction.atomic
def confirm_deadline(
    group_name: str, day: date, subject: str, task: str
) -> tuple[DeadlineStatus, Deadline]:
    group, _ = Group.objects.select_for_update().get_or_create(name=group_name)
    normalized_subject = normalize_text(subject)
    normalized_task = normalize_text(task)
    candidates = [
        deadline
        for deadline in Deadline.objects.select_for_update().filter(group=group, date=day).order_by("pk")
        if normalize_text(deadline.subject) == normalized_subject
    ]
    for deadline in candidates:
        if normalize_text(deadline.deadline) == normalized_task:
            return "unchanged", deadline

    if candidates:
        match = reconcile_homework(task, [deadline.deadline for deadline in candidates])
        if match.match_index is not None:
            deadline = candidates[match.match_index]
            merged = match.merged_homework.strip()
            if normalize_text(merged) == normalize_text(deadline.deadline):
                return "unchanged", deadline
            deadline.deadline = merged
            deadline.save(update_fields=["deadline"])
            return "updated", deadline

    return "created", Deadline.objects.create(
        group=group, date=day, subject=subject, deadline=task
    )
