from django.db import models
from accounts.models import User, Group
import datetime
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os


class Department(models.Model):
    name = models.CharField(unique=True, max_length=200)

    def __str__(self):
        return self.name


class Course(models.Model):
    name = models.CharField(unique=True, max_length=128)
    description = models.TextField(null=True, blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="courses",
        default=None,
        null=False,
    )
    lecturer = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name="courses", null=True, blank=True
    )
    groups = models.ManyToManyField(Group, related_name="courses", blank=True)
    course_workload = models.TextField(null=True, blank=True)
    syllabus_url = models.URLField(unique=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=datetime.datetime.now())
    id = models.AutoField(primary_key=True)

    def __str__(self):
        return f"{self.name}"


class Resource(models.Model):
    file = models.FileField(upload_to="study_resources/")
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="resources"
    )
    doc_ids = models.JSONField(default=list)
    file_hash = models.CharField(max_length=64, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.file}"


@receiver(post_delete, sender=Resource)
def delete_file_on_resource_delete(sender, instance, **kwargs):
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)
