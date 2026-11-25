from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic import RedirectView

handler403 = "gamelobby.errors.permission_denied"
handler404 = "gamelobby.errors.page_not_found"
handler500 = "gamelobby.errors.server_error"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="games:home"), name="site_home"),
    path("games/", include("lobby.urls")),
    path("facebook/", include("profiles.urls")),
    # Keep old GameLobby bookmarks working after moving it to /games/.
    path("login/", RedirectView.as_view(pattern_name="games:login")),
    path("register/", RedirectView.as_view(pattern_name="games:register")),
    path(
        "profile/<uuid:public_id>/",
        RedirectView.as_view(pattern_name="facebook:profile"),
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
