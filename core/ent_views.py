from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_GET

from .ent import get_ent_catalogue
from .localization import get_request_language
from .models import ENTSpecification


@login_required
@require_GET
def ent_specification(request, year):
    language = request.GET.get("language", get_request_language(request))
    if language not in {"ru", "kk", "kz"}:
        return JsonResponse({"error": "Unsupported language"}, status=400)
    try:
        data = get_ent_catalogue(year=year, language=language)
    except ENTSpecification.DoesNotExist:
        raise Http404("ENT specification not found")
    return JsonResponse(data)
