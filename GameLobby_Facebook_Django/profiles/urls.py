from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

app_name = "facebook"

urlpatterns = [
    path("", views.home, name="home"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
            template_name="registration/login.html",
        ),
        name="login",
    ),
    path("register/", views.register, name="register"),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="facebook:login"),
        name="logout",
    ),
    path("profile/<uuid:public_id>/", views.profile_page, name="profile"),
    path("profile/<uuid:public_id>/edit/", views.edit_profile, name="edit_profile"),
    path(
        "profile/<uuid:public_id>/posts/create/", views.create_post, name="create_post"
    ),
    path(
        "profile/<uuid:public_id>/posts/<int:post_id>/edit/",
        views.edit_post,
        name="edit_post",
    ),
    path(
        "profile/<uuid:public_id>/posts/<int:post_id>/delete/",
        views.delete_post,
        name="delete_post",
    ),
    path(
        "profile/<uuid:public_id>/photo/<str:kind>/",
        views.upload_photo,
        name="upload_photo",
    ),
]
