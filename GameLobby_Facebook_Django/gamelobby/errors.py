from django.shortcuts import render


def error_page(request, status):
    section = (
        "profiles"
        if request.path_info.startswith(("/facebook/", "/profile/"))
        else "games"
    )
    return render(request, f"{section}/{status}.html", status=status)


def permission_denied(request, exception):
    return error_page(request, 403)


def page_not_found(request, exception):
    return error_page(request, 404)


def server_error(request):
    return error_page(request, 500)
