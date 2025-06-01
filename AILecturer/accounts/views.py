from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def log_in(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        user = authenticate(request, email=email, password=password)
        next_url = request.GET.get("next")
        if not next_url:
            next_url = reverse("home:home")
        if user is not None:
            login(request, user)
            return redirect(next_url)
        else:
            messages.error(request, "Ви не пройшли ідентифікацію")
    return render(request, "auth/log_in.html")


def log_out(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect(reverse("home:home"))


@login_required(login_url="/accounts/auth/login/")
def user_profile(request):
    if request.method == "POST":
        first_name = request.POST.get("firstName")
        last_name = request.POST.get("lastName")
        email = request.POST.get("email")

        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
    return render(request, "accounts/profile.html")
