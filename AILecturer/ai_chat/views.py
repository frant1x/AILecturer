from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from courses.models import Course
from .models import ChatSession, Message
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .rag_utils import get_retriever, parse_docs, build_prompt
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from django.http import StreamingHttpResponse
import json


@login_required(login_url="/accounts/auth/login/")
def show_chat(request, course_id, session_id=None):
    course = get_object_or_404(Course, id=course_id)
    if request.user.role == 0:
        user_group = request.user.group
        if user_group is None or user_group not in course.groups.all():
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")
    elif request.user.role == 1:
        if request.user != course.lecturer:
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")

    chat_sessions = ChatSession.objects.filter(
        user=request.user, course=course_id
    ).order_by("-updated_at")

    messages = None
    if session_id:
        messages = Message.objects.filter(chat=session_id).order_by("created_at")

    context = {
        "course": course,
        "chat_sessions": chat_sessions,
        "messages": messages,
        "session_id": session_id,
    }
    return render(request, "ai_chat/ai_chat.html", context=context)


@login_required(login_url="/accounts/auth/login/")
@require_POST
def create_session(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.user.role == 0:
        user_group = request.user.group
        if user_group is None or user_group not in course.groups.all():
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")
    elif request.user.role == 1:
        if request.user != course.lecturer:
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")

    course = get_object_or_404(Course, id=course_id)
    session = ChatSession.objects.create(user=request.user, course=course)
    return redirect(
        reverse(
            "courses:ai_chat:show_chat_session",
            kwargs={"course_id": course_id, "session_id": session.id},
        )
    )


@login_required(login_url="/accounts/auth/login/")
@require_POST
def delete_session(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.user.role == 0:
        user_group = request.user.group
        if user_group is None or user_group not in course.groups.all():
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")
    elif request.user.role == 1:
        if request.user != course.lecturer:
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")

    session_id = request.POST.get("session_id")
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    session.delete()
    return redirect(
        reverse("courses:ai_chat:show_chat", kwargs={"course_id": course_id})
    )


@login_required(login_url="/accounts/auth/login/")
@require_POST
def get_answer(request, course_id, session_id):
    """
    Handle a user’s message in a chat session, retrieve relevant context using a vector store,
    generate an AI response, and stream it back to the client.
    """

    course = get_object_or_404(Course, id=course_id)
    if request.user.role == 0:
        user_group = request.user.group
        if user_group is None or user_group not in course.groups.all():
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")
    elif request.user.role == 1:
        if request.user != course.lecturer:
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")

    content = request.POST.get("content")
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)

    user_message = Message.objects.create(
        chat=session,
        sender=0,
        content=content,
    )

    retriever = get_retriever(course_id)
    docs = retriever.invoke(content)
    docs_by_type = parse_docs(docs)

    chain = (
        {
            "context": RunnableLambda(lambda _: docs_by_type),
            "question": RunnablePassthrough(),
        }
        | RunnableLambda(build_prompt)
        | ChatOpenAI(model="gpt-4o-mini", streaming=True)
        | StrOutputParser()
    )

    def stream_response():
        collected_text = ""
        for chunk in chain.stream(content):
            collected_text += chunk
            data = json.dumps({"partial": chunk})
            yield f"data: {data}\n\n"

        Message.objects.create(chat=session, sender=1, content=collected_text)
        yield "data: [DONE]\n\n"

    return StreamingHttpResponse(stream_response(), content_type="text/event-stream")
