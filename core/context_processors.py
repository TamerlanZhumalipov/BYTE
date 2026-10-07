from .localization import get_request_language


def site_language(request):
    return {"site_lang": get_request_language(request)}
