from django.shortcuts import render
from courses.models import Course
from django.http import JsonResponse


def home(request):
    return render(request, "home/home.html")


def autocomplete_courses(request):
    query = request.GET.get("q", "")
    results = []
    if query:
        courses = Course.objects.filter(name__icontains=query)[:10]
        results = [{"id": c.id, "name": c.name} for c in courses]
    return JsonResponse({"results": results})
