from django.db import models
from courses.models import Course
from accounts.models import User
import datetime

SENDER_CHOICES = (
    (0, "student"),
    (1, "bot"),
)


class ChatSession(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="chat_sessions"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="chat_sessions"
    )
    updated_at = models.DateTimeField(auto_now=datetime.datetime.now())

    def __str__(self):
        return f"Chat #{self.id} - {self.user.email}"


class Message(models.Model):
    chat = models.ForeignKey(
        ChatSession, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.IntegerField(choices=SENDER_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(editable=False, auto_now=datetime.datetime.now())

    def __str__(self):
        return f"{self.sender} - [{self.created_at:%Y-%m-%d %H:%M}]"
