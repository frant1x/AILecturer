from django.urls import path, include
from . import views


app_name = "courses"
urlpatterns = [
    path("", views.show_courses, name="show_courses"),
    path("my/", views.my_courses, name="my_courses"),
    path("<int:course_id>/", views.show_overview, name="show_overview"),
    path("<int:course_id>/edit/", views.edit_course, name="edit_course"),
    path("<int:course_id>/resources", views.show_resources, name="show_resources"),
    path("<int:course_id>/resources/add", views.add_resource, name="add_resource"),
    path(
        "<int:course_id>/resources/<int:resource_id>/delete",
        views.delete_resource,
        name="delete_resource",
    ),
    path("<int:course_id>/ai_chat/", include("ai_chat.urls")),
    path(
        "<int:course_id>/participants/",
        views.show_participants,
        name="show_participants",
    ),
]
