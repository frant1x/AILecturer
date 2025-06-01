import datetime
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


ROLE_CHOICES = (
    (0, "student"),
    (1, "lecturer"),
    (2, "admin"),
)


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user


class Group(models.Model):
    name = models.CharField(unique=True, max_length=20)

    def __str__(self):
        return f"{self.name}"


class User(AbstractBaseUser, PermissionsMixin):
    first_name = models.CharField(max_length=20, null=True, blank=True)
    last_name = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(max_length=100, unique=True, null=False)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    role = models.IntegerField(choices=ROLE_CHOICES, default=0)
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, related_name="students", null=True, blank=True
    )
    created_at = models.DateTimeField(editable=False, auto_now=datetime.datetime.now())
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    objects = CustomUserManager()

    def __str__(self):
        return f"{self.email}"

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.set_password(self.password)
        else:
            orig = User.objects.get(pk=self.pk)
            if self.password != orig.password:
                self.set_password(self.password)
        super().save(*args, **kwargs)
        if not self.avatar:
            self.generate_avatar()

    def generate_avatar(self):
        initials = self.email[:1].upper()
        image_size = (128, 128)
        background_color = "#0dcaf0"
        text_color = "#ffffff"
        image = Image.new("RGB", image_size, background_color)
        draw = ImageDraw.Draw(image)

        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except IOError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), initials, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_position = (
            (image_size[0] - text_width) // 2,
            (image_size[1] - text_height) // 2 - 10,
        )

        draw.text(text_position, initials, fill=text_color, font=font)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        image_file = ContentFile(buffer.getvalue(), name=f"{self.pk}_avatar.png")

        self.avatar.save(image_file.name, image_file, save=True)
