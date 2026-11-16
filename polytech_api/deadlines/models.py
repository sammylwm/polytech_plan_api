from django.db import models


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
