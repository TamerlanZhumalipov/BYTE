"""Verified bibliography only; never invent editions, translations or page ranges."""
import re
from .models import TextbookReference


def references():
    return TextbookReference.objects.filter(verified=True, textbook__is_active=True).select_related('textbook')


def serialize(ref):
    b = ref.textbook
    return dict(id=ref.pk, title=b.title, authors=b.authors, grade=b.grade,
                language=b.language, publisher=b.publisher, year=b.year,
                edition=b.edition, isbn=b.isbn, paragraph=ref.paragraph,
                paragraph_title=ref.title, page_start=ref.page_start, pdf_page=ref.pdf_page)


def for_topics(topic_ids, language='ru'):
    result = {pk: [] for pk in topic_ids}
    rows = references().filter(ent_topics__in=topic_ids).prefetch_related('ent_topics').distinct()
    rows = sorted(rows, key=lambda r: (r.textbook.language != language, r.page_start, r.pk))
    for ref in rows:
        for topic in ref.ent_topics.all():
            if topic.pk in result and len(result[topic.pk]) < 2:
                result[topic.pk].append(serialize(ref))
    return result


def book_reply(message, section=None, language='ru'):
    if not re.search(r'книг|учебник|почитать|страниц|параграф|кітап|оқулық|қай бет|не оқу', message, re.I):
        return None
    # Explicit subject keywords outrank the current lesson. Whole-word matching
    # prevents 'for' matching 'information'. Unmatched requests never guess pages.
    text = message.casefold()
    found = []
    for ref in references():
        keys = [k.strip().casefold() for k in ref.keywords.split(',') if k.strip()]
        if any(re.search(r'(?<!\w)' + re.escape(k) + r'(?!\w)', text) for k in keys):
            found.append(ref)
    if not found and section is not None and re.search(r'этой тем|этому раздел|осы тақырып', text):
        ids = []
        current = section
        while current:
            ids.append(current.pk)
            current = current.parent
        found = list(references().filter(sections__in=ids).distinct())
    # Message language wins over the UI when clearly identifiable.
    if re.search(r'кітап|оқулық|қай бет|осы тақырып|не оқу', text):
        language = 'kk'
    elif re.search(r'книг|учебник|почитать|страниц|параграф', text):
        language = 'ru'
    if not found:
        return ('Каталогта бұл сұраққа тексерілген сілтеме табылмады. Тақырыпты нақтылаңыз, мысалы: while немесе процессор.' if language == 'kk' else
                'В каталоге пока нет проверенной ссылки для этого запроса. Уточни тему, например: while или процессор.')
    found.sort(key=lambda r: (r.textbook.language != language, r.page_start, r.pk))
    lines = ['Тексерілген каталогтан:' if language == 'kk' else 'Из проверенного каталога:']
    for ref in found[:3]:
        b = ref.textbook
        lang = 'қазақша' if b.language == 'kk' else 'русский'
        grade = f'{b.grade}-сынып' if language == 'kk' else f'{b.grade} класс'
        page = f'{ref.page_start}-беттен бастап' if language == 'kk' else f'начиная со страницы {ref.page_start}'
        edition = f', {b.edition}' if b.edition else ''
        lines.append(f'«{b.title}», {grade}, {b.authors}. {b.publisher}, {b.year}{edition}. {lang}. § {ref.paragraph} «{ref.title}», {page}.')
    return '\n\n'.join(lines)
