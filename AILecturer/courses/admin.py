from django.contrib import admin

from .models import Department, Course, Resource

admin.site.register(Department)
admin.site.register(Course)
admin.site.register(Resource)
