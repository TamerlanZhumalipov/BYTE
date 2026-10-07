"""Read-only catalogue contract for the future Forecast Engine.

Mappings are candidate evidence sources, not official topic score weights.
Root mappings imply descendants; shared roots must not be counted twice in
an eventual aggregate forecast. Student evidence is deliberately not exposed.
"""
from django.db.models import Prefetch

from .models import ENTSpecification, ENTTopic, Section


def get_ent_catalogue(year=2026, subject="informatics", language="ru"):
    language = "kk" if language in {"kk", "kz"} else "ru"
    spec = ENTSpecification.objects.prefetch_related(Prefetch(
        "topics", queryset=ENTTopic.objects.prefetch_related(Prefetch(
            "sections", queryset=Section.objects.filter(parent__isnull=True, is_published=True),
        )),
    )).get(year=year, subject=subject)

    def title(obj):
        return (obj.title_kk or obj.title) if language == "kk" else obj.title

    return {
        "id": spec.pk, "year": spec.year, "subject": spec.subject,
        "title": title(spec), "title_ru": spec.title, "title_kk": spec.title_kk,
        "language": language, "question_count": spec.question_count,
        "max_score": spec.max_score,
        "source_url": spec.source_url, "source_url_kk": spec.source_url_kk,
        "topics": [{
            "id": topic.pk, "code": topic.code, "title": title(topic),
            "title_ru": topic.title, "title_kk": topic.title_kk,
            "mapping_notes": topic.mapping_notes,
            "sections": [{"id": section.pk, "slug": section.slug,
                          "title": title(section)} for section in topic.sections.all()],
        } for topic in spec.topics.all()],
    }
