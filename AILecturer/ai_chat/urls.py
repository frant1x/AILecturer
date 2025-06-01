from django.urls import path
from . import views


app_name = "ai_chat"
urlpatterns = [
    path("", views.show_chat, name="show_chat"),
    path("<int:session_id>/", views.show_chat, name="show_chat_session"),
    path("<int:session_id>/get_answer/", views.get_answer, name="get_answer"),
    path("create_session/", views.create_session, name="create_session"),
    path("delete_session/", views.delete_session, name="delete_session"),
]
