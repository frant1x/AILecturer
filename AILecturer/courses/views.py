from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Department, Course, Resource
from accounts.models import Group
import os
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from ai_chat.rag_utils import (
    pdf_partition,
    summarize_all,
    get_retriever,
    add_pdf,
    remove_pdf,
    get_file_hash,
)


@login_required(login_url="/accounts/auth/login/")
def show_courses(request):
    departments = Department.objects.all()
    courses = Course.objects.all()
    context = {"departments": departments, "courses": courses}
    return render(request, "courses/all_courses.html", context=context)


@login_required(login_url="/accounts/auth/login/")
def my_courses(request):
    if request.user.role == 0:
        courses = request.user.group.courses.all()
    elif request.user.role == 1:
        courses = request.user.courses.all()
    context = {"courses": courses}
    return render(request, "courses/my_courses.html", context=context)


@login_required(login_url="/accounts/auth/login/")
def show_overview(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.user.role == 0:
        user_group = request.user.group
        if user_group is None or user_group not in course.groups.all():
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")
    elif request.user.role == 1:
        if request.user != course.lecturer:
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")

    group_names = ", ".join(group.name for group in course.groups.all())
    groups = Group.objects.all()
    context = {"course": course, "course_groups": group_names, "groups": groups}
    return render(request, "courses/overview.html", context=context)


@login_required(login_url="/accounts/auth/login/")
@require_POST
def edit_course(request, course_id):
    if request.user.role == 1:
        course = get_object_or_404(Course, id=course_id)

        description = request.POST.get("description", "").strip()
        if description:
            course.description = description

        course_workload = request.POST.get("course_workload", "").strip()
        if course_workload:
            course.course_workload = course_workload

        syllabus_url = request.POST.get("syllabus", "").strip()
        if syllabus_url:
            course.syllabus_url = syllabus_url

        selected_groups = request.POST.getlist("groups")
        if selected_groups:
            course.groups.set(selected_groups)
        course.save()
        course.groups.set(selected_groups)
    return redirect(reverse("courses:show_overview", kwargs={"course_id": course_id}))


@login_required(login_url="/accounts/auth/login/")
def show_resources(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.user.role == 0:
        user_group = request.user.group
        if user_group is None or user_group not in course.groups.all():
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")
    elif request.user.role == 1:
        if request.user != course.lecturer:
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")

    resources = course.resources.all()
    resources_dict = {}
    for resource in resources:
        filepath = resource.file.name
        filepath = filepath[len("study_resources/") :]
        filename = os.path.splitext(filepath)[0]
        resources_dict[filename] = (resource.id, resource.file.url)
    context = {"course": course, "resources": resources_dict}
    return render(request, "courses/resources.html", context=context)


@login_required(login_url="/accounts/auth/login/")
@require_POST
def add_resource(request, course_id):
    """
    Handle POST request to upload a PDF file as a course resource.
    """

    course = get_object_or_404(Course, id=course_id)
    if request.user.role == 0:
        return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")
    elif request.user.role == 1:
        if request.user != course.lecturer:
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")

        if request.FILES.get("resource"):
            resource_file = request.FILES["resource"]

            if not resource_file.name.lower().endswith(".pdf"):
                messages.error(request, "Дозволено лише PDF-файли.")
                return redirect(
                    reverse("courses:show_resources", kwargs={"course_id": course_id})
                )

            file_hash = get_file_hash(resource_file)

            if course.resources.filter(file_hash=file_hash).exists():
                messages.error(request, "Цей файл вже було додано раніше.")
            else:
                resource = course.resources.create(
                    file=resource_file, file_hash=file_hash
                )

                texts, tables, images = pdf_partition(resource.file.path)
                text_summaries, table_summaries, image_summaries = summarize_all(
                    texts, tables, images
                )
                retriever = get_retriever(course_id)
                doc_ids = add_pdf(
                    course_id,
                    retriever,
                    texts,
                    text_summaries,
                    tables,
                    table_summaries,
                    images,
                    image_summaries,
                )
                resource.doc_ids = doc_ids
                resource.save()

    return redirect(reverse("courses:show_resources", kwargs={"course_id": course_id}))


@login_required(login_url="/accounts/auth/login/")
@require_POST
def delete_resource(request, course_id, resource_id):
    """
    Handle POST request to delete a resource and its associated data.
    """

    course = get_object_or_404(Course, id=course_id)
    if request.user.role == 0:
        return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")
    elif request.user.role == 1:
        if request.user != course.lecturer:
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")

        resource = Resource.objects.get(id=resource_id)

        retriever = get_retriever(course_id)
        remove_pdf(course_id, retriever, resource.doc_ids)

        resource.delete()
    return redirect(reverse("courses:show_resources", kwargs={"course_id": course_id}))


@login_required(login_url="/accounts/auth/login/")
def show_participants(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.user.role == 0:
        user_group = request.user.group
        if user_group is None or user_group not in course.groups.all():
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")
    elif request.user.role == 1:
        if request.user != course.lecturer:
            return HttpResponseForbidden("Ви не маєте доступу до цього курсу.")

    context = {"course": course}
    return render(request, "courses/participants.html", context=context)
