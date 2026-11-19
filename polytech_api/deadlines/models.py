from uuid import uuid4

from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver


class Group(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=7, unique=True)


class Deadline(models.Model):
    objects = models.Manager()
    date = models.DateField()
    subject = models.CharField()
    deadline = models.CharField()
    group = models.ForeignKey(
        Group,
        on_delete=models.PROTECT,
        related_name="deadlines",
    )


class DeadlineAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    deadline = models.ForeignKey(
        Deadline,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.FileField(upload_to="deadline-attachments/")
    name = models.CharField(max_length=255)
    size = models.PositiveBigIntegerField()


@receiver(post_delete, sender=DeadlineAttachment)
def delete_attachment_file(sender, instance, using, **kwargs):
    storage, name = instance.file.storage, instance.file.name
    if name:
        transaction.on_commit(lambda: storage.delete(name), using=using, robust=True)
