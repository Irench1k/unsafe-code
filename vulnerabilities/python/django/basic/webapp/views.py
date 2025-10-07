from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt


# `/`
def index(request):
    return HttpResponse(f"Index Page, Route: {request.path}")


# `/hello`
def hello(request):
    return HttpResponse(f"Hello, world!, Route: {request.path}")


# `/user/<username>`
def show_user(request, username):
    return HttpResponse(f"User: {username}, Route: {request.path}")


# `/user/<username>/<int:user_id>`
def show_user_details(request, username, user_id):
    return HttpResponse(
        f"Username: {username}, User ID: {user_id}, Route: {request.path}"
    )


# `/user?id=123&type=admin`
def show_user_with_params(request):
    user_id = request.GET.get("id")
    user_type = request.GET.get("type")
    return HttpResponse(
        f"User ID: {user_id}, User Type: {user_type}, Route: {request.path}"
    )


@csrf_exempt  # exempt the view from CSRF protection for simplicity
def submit(request):
    if request.method == "POST":
        name = request.POST.get("name", "No Name")
        return redirect(reverse("show_user", kwargs={"username": name}))
    else:
        return render(request, "webapp/submit.html")
