from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),  # Example route
    path("hello/", views.hello, name="hello"),
    path("user/<str:username>/", views.show_user, name="show_user"),
    path(
        "user/<str:username>/<int:user_id>/",
        views.show_user_details,
        name="show_user_details",
    ),
    path("user/", views.show_user_with_params, name="show_user_with_params"),
    path("submit/", views.submit, name="submit"),
]
